from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime, date
import hashlib
import os

from database import init_db, get_db, load_keys, DB_PATH
from crypto_utils import (encrypt_vote, decrypt_vote, sign_vote,
                          verify_signature, hash_voter_id)
from blockchain import Blockchain

app = Flask(__name__)
app.secret_key = os.urandom(24)

CANDIDATES = ["Candidate A", "Candidate B", "Candidate C"]
ADMIN_EMAIL = "admin@votechain.com"
ADMIN_PASSWORD = "votechain123"
AUDIT_PASSWORD = "audit@votechain"
MAX_FAILED = 5

bc = Blockchain()


def log_audit(event_type, voter_id=None, voter_hash=None, detail=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (event_type, voter_id, voter_hash, detail, timestamp) VALUES (?,?,?,?,?)",
        (event_type, voter_id, voter_hash, detail, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_last_block():
    conn = get_db()
    row = conn.execute("SELECT * FROM blockchain ORDER BY block_id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/voter-login", methods=["GET", "POST"])
def voter_login():
    if request.method == "POST":
        voter_id = request.form.get("voter_id", "").strip().upper()
        dob = request.form.get("dob", "").strip()
        ip = request.remote_addr

        conn = get_db()
        voter = conn.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,)).fetchone()

        conn.execute(
            "INSERT INTO login_attempts (voter_id, success, ip_address, timestamp) VALUES (?,?,?,?)",
            (voter_id, 0, ip, datetime.utcnow().isoformat())
        )
        conn.commit()

        if not voter:
            log_audit("FAILED_LOGIN", voter_id=voter_id, detail="Voter ID not found")
            conn.close()
            return render_template("voter_login.html", error="Invalid Voter ID or Date of Birth.")

        if voter["locked"]:
            log_audit("LOCKED_ACCOUNT_ACCESS", voter_id=voter_id, detail="Account locked")
            conn.close()
            return render_template("voter_login.html", error="Account locked due to multiple failed attempts.")

        try:
            dob_date = datetime.strptime(dob, "%Y-%m-%d").date()
            today = date.today()
            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            if age < 18:
                log_audit("UNDERAGE_LOGIN", voter_id=voter_id, detail=f"Age: {age}")
                conn.close()
                return render_template("voter_login.html", error="You must be 18 or older to vote.")
        except ValueError:
            conn.close()
            return render_template("voter_login.html", error="Invalid date format.")

        if voter["dob"] != dob:
            failed = voter["failed_attempts"] + 1
            locked = 1 if failed >= MAX_FAILED else 0
            conn.execute("UPDATE voters SET failed_attempts=?, locked=? WHERE voter_id=?",
                         (failed, locked, voter_id))
            conn.commit()
            log_audit("FAILED_LOGIN", voter_id=voter_id, detail=f"Wrong DOB. Attempt {failed}/{MAX_FAILED}")
            if locked:
                log_audit("ACCOUNT_LOCKED", voter_id=voter_id, detail="Max attempts reached")
            conn.close()
            return render_template("voter_login.html",
                                   error=f"Invalid credentials. {'Account locked.' if locked else f'Attempts: {failed}/{MAX_FAILED}'}")

        conn.execute("UPDATE login_attempts SET success=1 WHERE id=(SELECT MAX(id) FROM login_attempts WHERE voter_id=?)", (voter_id,))
        conn.execute("UPDATE voters SET failed_attempts=0 WHERE voter_id=?", (voter_id,))
        conn.commit()
        conn.close()

        session["voter_id"] = voter_id
        session["voter_name"] = voter["name"]
        log_audit("SUCCESSFUL_LOGIN", voter_id=voter_id)
        return redirect(url_for("vote"))

    return render_template("voter_login.html")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin"] = True
            log_audit("ADMIN_LOGIN", detail="Admin authenticated")
            return redirect(url_for("admin_dashboard"))
        log_audit("ADMIN_FAILED_LOGIN", detail=f"Email: {email}")
        return render_template("admin_login.html", error="Invalid admin credentials.")
    return render_template("admin_login.html")


@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


@app.route("/voter-logout")
def voter_logout():
    session.pop("voter_id", None)
    session.pop("voter_name", None)
    return redirect(url_for("index"))


@app.route("/audit-logout")
def audit_logout():
    session.pop("audit_auth", None)
    return redirect(url_for("index"))


@app.route("/vote", methods=["GET", "POST"])
def vote():
    if "voter_id" not in session:
        return redirect(url_for("voter_login"))

    voter_id = session["voter_id"]
    conn = get_db()
    voter = conn.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,)).fetchone()

    if voter["has_voted"]:
        conn.close()
        return render_template("already_voted.html", name=voter["name"])

    if request.method == "POST":
        candidate = request.form.get("candidate")
        if candidate not in CANDIDATES:
            conn.close()
            return render_template("vote.html", candidates=CANDIDATES,
                                   name=voter["name"], error="Invalid candidate selection.")

        private_pem, public_pem = load_keys()
        voter_hash = hash_voter_id(voter_id)

        existing = conn.execute("SELECT * FROM votes WHERE voter_hash=?", (voter_hash,)).fetchone()
        if existing:
            log_audit("DUPLICATE_VOTE", voter_id=voter_id, voter_hash=voter_hash,
                      detail=f"Attempted duplicate for {candidate}")
            conn.close()
            return render_template("already_voted.html", name=voter["name"])

        encrypted = encrypt_vote(candidate, public_pem)
        signature = sign_vote(encrypted, private_pem)
        timestamp = datetime.utcnow().isoformat()

        last_block = get_last_block()
        prev_hash = last_block["current_hash"] if last_block else "0" * 64
        next_block_id = (last_block["block_id"] + 1) if last_block else 1

        new_block = bc.add_block(voter_hash, encrypted, signature, prev_hash, block_id=next_block_id)

        conn.execute(
            "INSERT INTO blockchain (block_id, voter_hash, encrypted_vote, timestamp, digital_signature, previous_hash, current_hash) VALUES (?,?,?,?,?,?,?)",
            (new_block.block_id, new_block.voter_hash, new_block.encrypted_vote,
             new_block.timestamp, new_block.digital_signature,
             new_block.previous_hash, new_block.current_hash)
        )
        conn.execute(
            "INSERT INTO votes (voter_hash, candidate, encrypted_vote, signature, block_id, timestamp) VALUES (?,?,?,?,?,?)",
            (voter_hash, candidate, encrypted, signature, new_block.block_id, timestamp)
        )
        conn.execute("UPDATE voters SET has_voted=1 WHERE voter_id=?", (voter_id,))
        conn.commit()
        conn.close()

        log_audit("VOTE_CAST", voter_id=voter_id, voter_hash=voter_hash, detail=f"Block {new_block.block_id}")

        session["last_vote"] = {
            "candidate": candidate,
            "encrypted": encrypted,
            "signature": signature,
            "block_id": new_block.block_id
        }
        return redirect(url_for("receipt"))

    conn.close()
    return render_template("vote.html", candidates=CANDIDATES, name=voter["name"])


@app.route("/receipt")
def receipt():
    if "voter_id" not in session or "last_vote" not in session:
        return redirect(url_for("index"))
    vote_data = session["last_vote"]
    return render_template("receipt.html", vote=vote_data, name=session.get("voter_name"))


@app.route("/explorer")
def explorer():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db()
    blocks = [dict(r) for r in conn.execute("SELECT * FROM blockchain ORDER BY block_id ASC").fetchall()]
    conn.close()
    _, public_pem = load_keys()

    for b in blocks:
        if b["block_id"] == 0:
            b["sig_status"] = "GENESIS"
        else:
            b["sig_status"] = "VALID" if verify_signature(b["encrypted_vote"], b["digital_signature"], public_pem) else "INVALID"

    return render_template("explorer.html", blocks=blocks)


@app.route("/api/verify-chain")
def api_verify_chain():
    conn = get_db()
    blocks = [dict(r) for r in conn.execute("SELECT * FROM blockchain ORDER BY block_id ASC").fetchall()]
    conn.close()
    valid, message = bc.verify_chain(blocks[1:] if blocks else [])  
    valid, message = bc.verify_chain(blocks)
    return jsonify({"valid": valid, "message": message})


@app.route("/audit", methods=["GET", "POST"])
def audit():
    if not session.get("audit_auth"):
        if request.method == "POST":
            if request.form.get("password") == AUDIT_PASSWORD:
                session["audit_auth"] = True
            else:
                return render_template("audit_login.html", error="Incorrect password.")
        else:
            return render_template("audit_login.html")

    conn = get_db()

    failed_logins = [dict(r) for r in conn.execute(
        "SELECT * FROM login_attempts WHERE success=0 ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()]
    locked_accounts = [dict(r) for r in conn.execute(
        "SELECT * FROM voters WHERE locked=1"
    ).fetchall()]
    suspicious = [dict(r) for r in conn.execute(
        """SELECT voter_id, COUNT(*) as cnt FROM login_attempts
           WHERE success=0 GROUP BY voter_id HAVING cnt >= 3 ORDER BY cnt DESC"""
    ).fetchall()]
  
    vote_counts = [dict(r) for r in conn.execute(
        "SELECT voter_hash, COUNT(*) as vote_count FROM votes GROUP BY voter_hash"
    ).fetchall()]
    for vc in vote_counts:
        vc["status"] = "DUPLICATE VOTE REJECTED" if vc["vote_count"] > 1 else "OK"

    _, public_pem = load_keys()
    votes = [dict(r) for r in conn.execute("SELECT * FROM votes").fetchall()]
    for v in votes:
        v["sig_valid"] = verify_signature(v["encrypted_vote"], v["signature"], public_pem)

    blocks = [dict(r) for r in conn.execute("SELECT * FROM blockchain ORDER BY block_id ASC").fetchall()]
    chain_valid, chain_msg = bc.verify_chain(blocks)

    dup_events = [dict(r) for r in conn.execute(
        "SELECT * FROM audit_logs WHERE event_type='DUPLICATE_VOTE' ORDER BY timestamp DESC"
    ).fetchall()]

    conn.close()
    return render_template("audit.html",
        failed_logins=failed_logins,
        locked_accounts=locked_accounts,
        suspicious=suspicious,
        vote_counts=vote_counts,
        votes=votes,
        chain_valid=chain_valid,
        chain_msg=chain_msg,
        dup_events=dup_events
    )


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    private_pem, public_pem = load_keys()

    tally = {}
    for c in CANDIDATES:
        row = conn.execute("SELECT COUNT(*) as cnt FROM votes WHERE candidate=?", (c,)).fetchone()
        tally[c] = row["cnt"]

    total_votes = sum(tally.values())
    total_voters = conn.execute("SELECT COUNT(*) as cnt FROM voters").fetchone()["cnt"]

    votes = [dict(r) for r in conn.execute(
        "SELECT id, block_id, encrypted_vote, signature, timestamp FROM votes ORDER BY timestamp DESC"
    ).fetchall()]
    for v in votes:
        v["sig_valid"] = verify_signature(v["encrypted_vote"], v["signature"], public_pem)

    blocks = [dict(r) for r in conn.execute("SELECT * FROM blockchain ORDER BY block_id ASC").fetchall()]

    conn.close()
    return render_template("admin.html",
        tally=tally,
        total_votes=total_votes,
        total_voters=total_voters,
        votes=votes,
        blocks=blocks,
        candidates=CANDIDATES
    )


@app.route("/api/decrypt-vote/<int:vote_id>")
def api_decrypt_vote(vote_id):
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 403
    private_pem, _ = load_keys()
    conn = get_db()
    row = conn.execute("SELECT * FROM votes WHERE id=?", (vote_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Vote not found"}), 404
    try:
        plaintext = decrypt_vote(row["encrypted_vote"], private_pem)
        return jsonify({"plaintext": plaintext})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

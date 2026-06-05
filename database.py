import sqlite3
import os
from datetime import date, datetime
from crypto_utils import generate_rsa_keys, hash_voter_id

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "votechain.db")
KEYS_PATH = os.path.join(os.path.dirname(__file__), "instance", "keys.txt")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            dob TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0,
            failed_attempts INTEGER DEFAULT 0,
            locked INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_hash TEXT NOT NULL,
            candidate TEXT NOT NULL,
            encrypted_vote TEXT NOT NULL,
            signature TEXT NOT NULL,
            block_id INTEGER,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS blockchain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER UNIQUE NOT NULL,
            voter_hash TEXT NOT NULL,
            encrypted_vote TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            digital_signature TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            current_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            voter_id TEXT,
            voter_hash TEXT,
            detail TEXT,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id TEXT NOT NULL,
            success INTEGER NOT NULL,
            ip_address TEXT,
            timestamp TEXT NOT NULL
        );
    """)

    # Sample voters: voter_id, name, dob (YYYY-MM-DD)
    sample_voters = [
        ("VC001", "Arjun Sharma",     "1990-03-15"),
        ("VC002", "Priya Nair",       "1985-07-22"),
        ("VC003", "Rohan Mehta",      "1998-11-05"),
        ("VC004", "Sneha Iyer",       "2000-01-30"),
        ("VC005", "Vikram Patel",     "1975-09-18"),
    ]
    for vid, name, dob in sample_voters:
        c.execute("INSERT OR IGNORE INTO voters (voter_id, name, dob) VALUES (?,?,?)",
                  (vid, name, dob))

    conn.commit()
    conn.close()

    # Generate and store RSA keys if not present
    if not os.path.exists(KEYS_PATH):
        private_pem, public_pem = generate_rsa_keys()
        with open(KEYS_PATH, "w") as f:
            f.write("PRIVATE_KEY\n")
            f.write(private_pem)
            f.write("PUBLIC_KEY\n")
            f.write(public_pem)
    
    # Add genesis block if chain is empty
    conn = get_db()
    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM blockchain").fetchone()[0]
    if count == 0:
        from blockchain import Blockchain
        bc = Blockchain()
        genesis = bc.create_genesis_block()
        c.execute("""INSERT INTO blockchain 
            (block_id, voter_hash, encrypted_vote, timestamp, digital_signature, previous_hash, current_hash)
            VALUES (?,?,?,?,?,?,?)""",
            (genesis.block_id, genesis.voter_hash, genesis.encrypted_vote,
             genesis.timestamp, genesis.digital_signature,
             genesis.previous_hash, genesis.current_hash))
        conn.commit()
    conn.close()


def load_keys():
    with open(KEYS_PATH, "r") as f:
        content = f.read()
    priv_start = content.index("-----BEGIN RSA PRIVATE KEY-----")
    priv_end = content.index("-----END RSA PRIVATE KEY-----") + len("-----END RSA PRIVATE KEY-----") + 1
    private_pem = content[priv_start:priv_end]

    pub_start = content.index("-----BEGIN PUBLIC KEY-----")
    pub_end = content.index("-----END PUBLIC KEY-----") + len("-----END PUBLIC KEY-----") + 1
    public_pem = content[pub_start:pub_end]

    return private_pem, public_pem

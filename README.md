# Vote Chain — Blockchain-Based Voting System

A cryptographically secured digital voting system built with Flask, SQLite, RSA encryption, SHA-256 hashing, digital signatures, and a custom blockchain implementation.

---

## Project Structure

```
votechain/
├── app.py                  # Flask application & all routes
├── blockchain.py           # Custom blockchain (Block + Blockchain classes)
├── crypto_utils.py         # RSA encrypt/decrypt, sign, verify, SHA-256
├── database.py             # SQLite init, schema, key loading
├── setup.py                # One-time setup script
├── requirements.txt
├── instance/
│   ├── votechain.db        # SQLite database (auto-created)
│   └── keys.txt            # RSA key pair (auto-generated)
├── templates/
│   ├── base.html           # Shared layout + navbar
│   ├── index.html          # Homepage
│   ├── voter_login.html    # Voter authentication
│   ├── admin_login.html    # Admin authentication
│   ├── vote.html           # Ballot page
│   ├── receipt.html        # Vote confirmation
│   ├── already_voted.html  # Duplicate vote screen
│   ├── explorer.html       # Blockchain Explorer
│   ├── audit.html          # Audit Center
│   └── admin.html          # Admin Dashboard
└── static/
    ├── css/style.css        # Dark glassmorphism UI
    └── js/main.js           # Animations & interactivity
```

---

## Database Schema

| Table | Columns |
|---|---|
| `voters` | id, voter_id, name, dob, has_voted, failed_attempts, locked |
| `votes` | id, voter_hash, candidate, encrypted_vote, signature, block_id, timestamp |
| `blockchain` | id, block_id, voter_hash, encrypted_vote, timestamp, digital_signature, previous_hash, current_hash |
| `audit_logs` | id, event_type, voter_id, voter_hash, detail, timestamp |
| `login_attempts` | id, voter_id, success, ip_address, timestamp |

---

## Quick Start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Run setup (first time only)

```bash
python setup.py
```

This will:
- Create the SQLite database with all tables
- Generate RSA-2048 key pair
- Add the genesis block to the blockchain
- Insert 5 sample voter records

### 3. Start the server

```bash
python app.py
```

### 4. Open in browser

```
http://localhost:5000
```

---

## Credentials

### Voter Credentials

| Voter ID | Date of Birth |
|----------|--------------|
| VC001    | 1990-03-15   |
| VC002    | 1985-07-22   |
| VC003    | 1998-11-05   |
| VC004    | 2000-01-30   |
| VC005    | 1975-09-18   |

### Admin Credentials

| Field    | Value                   |
|----------|-------------------------|
| Email    | admin@votechain.com     |
| Password | votechain123            |

---

## Pages

| URL | Description |
|-----|-------------|
| `/` | Homepage |
| `/voter-login` | Voter login (ID + DOB) |
| `/admin-login` | Admin login |
| `/vote` | Ballot page (post-login) |
| `/receipt` | Vote confirmation with crypto details |
| `/explorer` | Blockchain Explorer |
| `/audit` | Audit Center |
| `/admin` | Admin Dashboard |

---

## Cryptography

- **RSA-2048 OAEP** — vote encryption/decryption
- **PSS-SHA256** — digital signatures
- **SHA-256** — blockchain hashing, voter ID hashing
- Each block contains: block ID, hashed voter ID, encrypted vote, timestamp, digital signature, previous hash, current hash

## Security Features

- One vote per voter (enforced by voter hash)
- Account lockout after 5 failed login attempts
- Age verification (18+ required)
- Chain integrity verification button
- Full audit trail of all events

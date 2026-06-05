import hashlib
import base64
import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


def generate_rsa_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return private_pem, public_pem


def encrypt_vote(plaintext_vote, public_pem):
    public_key = serialization.load_pem_public_key(
        public_pem.encode(), backend=default_backend()
    )
    ciphertext = public_key.encrypt(
        plaintext_vote.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(ciphertext).decode()


def decrypt_vote(ciphertext_b64, private_pem):
    private_key = serialization.load_pem_private_key(
        private_pem.encode(), password=None, backend=default_backend()
    )
    ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext.decode()


def sign_vote(encrypted_vote_b64, private_pem):
    private_key = serialization.load_pem_private_key(
        private_pem.encode(), password=None, backend=default_backend()
    )
    signature = private_key.sign(
        encrypted_vote_b64.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode()


def verify_signature(encrypted_vote_b64, signature_b64, public_pem):
    try:
        public_key = serialization.load_pem_public_key(
            public_pem.encode(), backend=default_backend()
        )
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            encrypted_vote_b64.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False


def hash_voter_id(voter_id):
    return hashlib.sha256(voter_id.encode()).hexdigest()


def sha256_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()

import hashlib
import json
import time
from datetime import datetime


class Block:
    def __init__(self, block_id, voter_hash, encrypted_vote, digital_signature, previous_hash):
        self.block_id = block_id
        self.voter_hash = voter_hash
        self.encrypted_vote = encrypted_vote
        self.timestamp = datetime.utcnow().isoformat()
        self.digital_signature = digital_signature
        self.previous_hash = previous_hash
        self.current_hash = self.compute_hash()

    def compute_hash(self):
        block_data = json.dumps({
            "block_id": self.block_id,
            "voter_hash": self.voter_hash,
            "encrypted_vote": self.encrypted_vote,
            "timestamp": self.timestamp,
            "digital_signature": self.digital_signature,
            "previous_hash": self.previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(block_data.encode()).hexdigest()

    def to_dict(self):
        return {
            "block_id": self.block_id,
            "voter_hash": self.voter_hash,
            "encrypted_vote": self.encrypted_vote,
            "timestamp": self.timestamp,
            "digital_signature": self.digital_signature,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
        }


class Blockchain:
    def __init__(self):
        self.chain = []

    def create_genesis_block(self):
        genesis = Block(
            block_id=0,
            voter_hash="GENESIS",
            encrypted_vote="GENESIS_BLOCK",
            digital_signature="GENESIS_SIGNATURE",
            previous_hash="0" * 64,
        )
        return genesis

    def add_block(self, voter_hash, encrypted_vote, digital_signature, previous_hash, block_id=None):
        if block_id is None:
            block_id = 1
        block = Block(block_id, voter_hash, encrypted_vote, digital_signature, previous_hash)
        return block

    def verify_chain(self, blocks):
        """Verify a list of block dicts from the database."""
        if not blocks:
            return True, "Chain is empty."
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i - 1]
            # Recompute hash
            block_data = json.dumps({
                "block_id": current["block_id"],
                "voter_hash": current["voter_hash"],
                "encrypted_vote": current["encrypted_vote"],
                "timestamp": current["timestamp"],
                "digital_signature": current["digital_signature"],
                "previous_hash": current["previous_hash"],
            }, sort_keys=True)
            expected_hash = hashlib.sha256(block_data.encode()).hexdigest()
            if current["current_hash"] != expected_hash:
                return False, f"Block {current['block_id']} hash mismatch — tampering detected."
            if current["previous_hash"] != previous["current_hash"]:
                return False, f"Block {current['block_id']} previous hash mismatch — chain broken."
        return True, "Blockchain integrity verified. All blocks are valid."

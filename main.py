from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

import hashlib

"""
Class to represent a transaction inside a block
The public key is the address of the user
"""


class Transaction:

    def __init__(self, sender_public_key, sender_private_key, recipient_public_key, amount):
        self.sender_public_key = sender_public_key
        self.sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.timestamp = datetime.now()

    def to_dict(self):
        return {"sender_public_key": self.sender_public_key,
                "recipient_public_key": self.recipient_public_key,
                "amount": self.amount,
                "timestamp": self.timestamp}

    def sign(self):
        return self.sender_private_key.sign(
            str(self.to_dict()).encode("ascii"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

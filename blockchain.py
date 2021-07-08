import binascii
import uuid
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

import hashlib

"""
Class to represent a transaction inside a block
The public key is the address of the user
"""


class Transaction:
    # Creates a transaction object, where
    # keys are of type cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey(/RSAPublicKey)
    # amount = floating point
    def __init__(self, sender_public_key, sender_private_key, recipient_public_key, amount):
        self.sender_public_key = sender_public_key
        self._sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.timestamp = datetime.now()

    # Function returns a dictionary of this transaction, without the private key
    def to_dict(self) -> dict:
        return {"sender_public_key": self.sender_public_key,
                "recipient_public_key": self.recipient_public_key,
                "amount": self.amount,
                "timestamp": self.timestamp}

    # Function converts this object to a string, without the private key
    def __str__(self) -> str:
        return str(self.to_dict())

    # Function creates a signature of this transaction, signed by the private key of the sender
    def sign(self) -> bytes:
        return self._sender_private_key.sign(
            str(self).encode("ascii"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def is_valid(self) -> bool:
        return True


class Block:
    def __init__(self, transactions, previous_block_hash):
        self.block_ID = uuid.uuid4()
        self.transactions = transactions
        self.proof_of_work = 0
        self.previous_block_hash = previous_block_hash

    def hash(self) -> bytes:
        hash_creator = hashlib.sha256()
        for transaction in self.transactions:
            hash_creator.update(str(transaction).encode("ascii"))
        hash_creator.update(self.block_ID)
        hash_creator.update(self.previous_block_hash)
        hash_creator.update(self.proof_of_work)
        return hash_creator.digest()

    def is_valid(self) -> bool:
        is_all_valid = True
        for transaction in self.transactions:
            if transaction.is_valid():
                is_all_valid = False
        return is_all_valid


class Wallet:
    def __init__(self, generate_keys=True):
        if generate_keys:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
        else:
            self.private_key = self.public_key = None

    # Function creates a new Wallet object with private/public keys given in an ascii format
    @classmethod
    def from_ascii_keys(cls, private_key, public_key):
        wallet = cls(False)
        wallet.private_key = Wallet.serialize_ascii_private_key(private_key)
        wallet.public_key = Wallet.serialize_ascii_public_key(public_key)
        return wallet

    @classmethod
    def from_binary_keys(cls, private_key, public_key):
        wallet = cls(False)
        wallet.private_key = serialization.load_der_private_key(private_key, None)
        wallet.public_key = serialization.load_der_public_key(public_key)
        return wallet

    # Function loads an ascii key to form a cryptography.hazmat RSA public key
    @staticmethod
    def serialize_ascii_public_key(ascii_key):
        return serialization.load_der_public_key(binascii.unhexlify(ascii_key))

    # Function loads an ascii key to form a cryptography.hazmat RSA private key
    @staticmethod
    def serialize_ascii_private_key(ascii_key, password=None):
        return serialization.load_der_private_key(binascii.unhexlify(ascii_key), password)

    # Function returns both (private key, public key) pair in bytes
    def keys_to_bytes(self):
        return (self.private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()),
                self.public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))

    # Function returns both (private key,public key) pair in an ascii encoding
    def keys_to_ascii(self):
        return tuple(binascii.hexlify(key).decode("ascii") for key in self.keys_to_bytes())


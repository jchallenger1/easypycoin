import base64
import binascii
import uuid
import hashlib
import database as dbmodels

from flask_sqlalchemy import SQLAlchemy
from typing import List, Tuple, Union
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

db = SQLAlchemy()

# The number of zeros the blockchain will search for on a sha256 hash for a proof of work
num_of_zeros = 4

# The reward for mining a block
block_mining_reward = 20


class Transaction:
    """Class represents a transaction inside a block"""

    def __init__(
            self,
            sender_public_key: RSAPublicKey,
            sender_private_key: Union[None, RSAPrivateKey],
            recipient_public_key: RSAPublicKey,
            amount: int, trans_uuid: uuid.UUID):
        self.sender_public_key = sender_public_key
        self.sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.uuid = trans_uuid
        self.signature = b""

    def to_binary_dict(self) -> dict:
        # Function returns a dictionary of this transaction, without the private key
        return {
            "sender_public_key": self.sender_public_key,
            "recipient_public_key": self.recipient_public_key,
            "amount": self.amount,
            "uuid": self.uuid
        }

    def to_ascii_dict(self) -> dict:
        # Similarly, function returns an ascii dictionary of this transaction, without the private key
        return {
            "sender_public_key": binary_to_ascii(
                self.sender_public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)),
            "recipient_public_key": binary_to_ascii(
                self.recipient_public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)),
            "amount": self.amount,
            "uuid": str(self.uuid)
        }

    def __str__(self) -> str:
        # Function converts this object to a string, without the private key
        return str(self.to_ascii_dict())

    def sign(self):
        # Function creates and sets the signature of this transaction, signed by the private key of the sender
        self.signature = self.sender_private_key.sign(
            str(self).encode("ascii"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    def is_valid(self) -> bool:
        # Function checks if this transaction is valid by verifying the signature with the sender's public key

        # Signature wasn't set
        if len(self.signature) == 0:
            return False

        # Use public key to verify signature
        try:
            self.sender_public_key.verify(
                self.signature,
                str(self).encode("ascii"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False


class Block:
    """
        Class represents a block used in a blockchain, a block itself may have multiple transactions
        Note that when mining, it's expected that the final block/bytes given is:
        [miner's public key]|[block's mining input]|[proof of work]
    """

    def __init__(self, transactions: List[Transaction], previous_block_hash: str):
        self.transactions = transactions
        self.proof_of_work = 0
        self.previous_block_hash = previous_block_hash
        self.uuid = uuid.uuid4()
        self.miner_key = None  # The key of the person who mined this block

    def get_mining_input(self) -> str:
        # Returns the mining representation of this block, used by miners
        return str(base64.b64encode(self.to_bytes()), "utf-8")

    def to_bytes(self, include_proof_of_work=False, include_miner_key=False) -> bytes:
        # Gets this current block to bytes
        # proof of work is optional as the miner is expected to create the proof of work
        # miner key is optional as the miner is expected to provide their miner key

        mining_bytes = bytearray()

        if include_miner_key:
            mining_bytes += str(self.miner_key).encode("ascii")

        # Add in each transaction and this block's information
        for transaction in self.transactions:
            mining_bytes += str(transaction).encode("ascii")
        mining_bytes += bytes.fromhex(self.previous_block_hash)
        mining_bytes += str(self.uuid).encode("ascii")

        if include_proof_of_work:
            mining_bytes += str(self.proof_of_work).encode("ascii")

        return mining_bytes

    def hash(self, include_proof_of_work=True, include_miner_key=False) -> str:
        # Gets the SHA256 hash digest in hexadecimal, both proof of work and miner key is optional,
        # however when verifying if this block is mined and begins with x amount of zeros, both should be set to true
        return hashlib.sha256(self.to_bytes(include_proof_of_work, include_miner_key)).hexdigest()

    def check_proof_of_work(self, other_proof: int, miner_public_key: str) -> str:
        # Function checks if the proof of work given with the miner's key results in n amount of zeros
        # Function returns an error message - empty string if this proof of work works with this block

        # Set the proof and miner's key
        previous_proof = self.proof_of_work
        self.proof_of_work = other_proof
        self.miner_key = miner_public_key

        # Get the hash of this block and verify if it begins with n amount of zeros at start
        block_hash = self.hash(include_proof_of_work=True, include_miner_key=True)
        start_num_zeros = '0' * num_of_zeros

        if not block_hash.startswith(start_num_zeros):
            self.proof_of_work = previous_proof
            self.miner_key = None
            return f"Proof of work {other_proof} gave SHA256 {block_hash} which does not start with {start_num_zeros}"
        return ""

    def is_valid(self) -> bool:
        # Function checks this block is valid, defined by all transactions being valid plus
        # the hash begins with n amount of zeros (TODO)
        return all(transaction.is_valid() for transaction in self.transactions)

    def __str__(self) -> str:
        # Function converts this object to a string, without the private key
        return str(dict(self))

    def __iter__(self):
        # For dict(), create a generator
        yield "uuid", str(self.uuid)
        yield "transactions", [trans.to_ascii_dict() for trans in self.transactions]
        yield "previous_block_hash", self.previous_block_hash
        yield "proof_of_work", self.proof_of_work

    @staticmethod
    def genesis_block():
        # Creates a genesis block with no transactions
        hash_creator = hashlib.sha256()
        hash_creator.update(b"0")  # Value from constructor
        return Block([], hash_creator.digest().hex())


class BlockChain:
    """Class represents an entire block chain, this class as well acts as a coinbase"""

    def __init__(self):
        self.transactions = []  # All transactions given to the coinbase not present in the chain
        self.minable_blocks = []  # All blocks that we can give to the user under a request to mine a block
        self.chain = [Block.genesis_block()]  # The block chain
        self.used_block_uuids = set()  # All uuids ever given out for a block generated in this class
        self.nodes = set()  # All other coinbases (nodes)
        self.node_uuid = uuid.uuid4()  # uuid of our own coinbase
        # indicator flag to create new blocks from transactions or keep the ones in minable blocks
        self.create_new_mining_blocks = True

    max_transactions_const = 3  # maximum amount of transactions that can fit into a block

    def create_mining_blocks(self) -> None:
        # Function creates the minable blocks from the transactions given to the coinbase
        # TODO: Allow for blocks to be added while mining is occuring - low priority

        if not self.create_new_mining_blocks:
            print("Flag indicates not to make any new blocks")
            return None

        if len(self.transactions) < 1:
            print("Not enough transactions to make a block")
            return None

        # Create all new mining blocks
        prev_block_hash = self.chain[-1].hash()

        # partition transactions into n sized arrays to put into each block
        for i in range(0, len(self.transactions), BlockChain.max_transactions_const):
            transaction_blocks = self.transactions[i:i + BlockChain.max_transactions_const]
            block = Block(transaction_blocks, prev_block_hash)
            self.minable_blocks.append(block)
            self.used_block_uuids.add(block.uuid)

        self.create_new_mining_blocks = False

    def clear_mining_blocks(self) -> None:
        # Function simply clears the mining blocks and allows for more mining blocks to be generated
        self.minable_blocks.clear()
        self.create_new_mining_blocks = True

    def add_transaction(self, transaction: Transaction) -> None:
        # Function adds a transaction to the coinbase
        self.transactions.append(transaction)

    def find_mine_block(self, block_uuid: uuid) -> Union[Tuple[str, Block], Tuple[str, None]]:
        # Function finds a mining block given the block's uuid
        # Returns an error message and Block pair

        # First find the block the user is trying to mine
        found_block = None
        # Look in minable blocks
        for block in self.minable_blocks:
            if block.uuid == block_uuid:
                found_block = block
                break

        # Block was not found
        if found_block is None:

            # Check if it's already in the blockchain
            block_already_minded = False
            for block in self.chain:
                if block.uuid == block_uuid:
                    block_already_minded = True
                    break
            if block_already_minded:
                return "This block has already been mined and is in the blockchain", None

            # Check if it's an invalid block by someone else mining a different one, thus this block has an incorrect
            # previous hash
            if block_uuid in self.used_block_uuids:
                return "This block is no longer valid due to a blockchain addition", None

            # Block didn't exist
            return f"This block with uuid {block_uuid} does not exist!", None

        return "", found_block

    def move_minable_block(self, block: Block) -> Union[None, str]:
        # Function moves a block that is from self.transactions to the chain
        # TODO: add a block.validate here

        try:
            self.minable_blocks.remove(block)
            for transaction in block.transactions:
                self.transactions.remove(transaction)
        except ValueError as e:
            return f"Failure trying to remove block {block.uuid}, {str(e)}"
        self.chain.append(block)


class Wallet(db.Model):
    """Class represents a coinbase wallet, of which is an RSA private/public key pair"""
    public_key = db.Column(dbmodels.KeyType, primary_key=True)
    balance = db.Column(db.Integer, nullable=True)

    def __init__(self, generate_keys=True):
        self.private_key = None
        self.public_key = db.Column(dbmodels.KeyType, primary_key=True)
        if generate_keys:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=512
            )
            self.public_key = self.private_key.public_key()

    @classmethod
    def from_ascii_keys(cls, private_key: str, public_key: str):
        # Function creates a new Wallet object with private/public keys given in an ascii format
        wallet = cls(False)
        wallet.private_key = ascii_key_to_private_key(private_key)
        wallet.public_key = ascii_key_to_public_key(public_key)
        return wallet

    @classmethod
    def from_binary_keys(cls, private_key: bytes, public_key: bytes):
        # Function creates a new Wallet object with private/public keys given in a binary format
        wallet = cls(False)
        wallet.private_key = serialization.load_der_private_key(private_key, None)
        wallet.public_key = serialization.load_der_public_key(public_key)
        return wallet

    def keys_to_bytes(self) -> Tuple[bytes, bytes]:
        # Function returns both (private key, public key) pair in bytes

        return (self.private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()),
                self.public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))

    def keys_to_ascii(self) -> Tuple[str, ...]:
        # Function returns both (private key,public key) pair in an ascii encoding
        return tuple(binary_to_ascii(key) for key in self.keys_to_bytes())


def binary_to_ascii(binary_item: bytes) -> str:
    # Function converts bytes to an ascii string
    return binascii.hexlify(binary_item).decode("ascii")


def ascii_to_binary(ascii_item: str) -> bytes:
    # Function converts an ascii string to bytes
    return binascii.unhexlify(ascii_item)


def ascii_key_to_public_key(ascii_key: str) -> RSAPublicKey:
    # function converts an ascii representation of a public key to bytes
    return serialization.load_der_public_key(binascii.unhexlify(ascii_key))


def ascii_key_to_private_key(ascii_key: str, password: bytes = None) -> RSAPrivateKey:
    # Function loads an ascii key to form a RSA private key
    return serialization.load_der_private_key(binascii.unhexlify(ascii_key), password)


def serializer(obj):
    # Function specifically for json.dumps serialization, simply allows for serialization for this file's objects
    if isinstance(obj, Transaction):
        return obj.to_ascii_dict()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, Block):
        return str(obj)
    return obj.__dict__

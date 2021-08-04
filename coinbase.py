import json
import uuid
from typing import Union

import cryptography.exceptions

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from flask import Flask, jsonify, request, render_template
from sqlalchemy import func

import blockchain as crypto
from blockchain import Transaction, BlockChain, CoinBase, Block, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blockchain.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

port = 5000
blockchain = BlockChain()
coinbase = CoinBase(None, None, "")  # is set in app.app_context()

with app.app_context():
    db.create_all()
    blockchain.check_genesis_block()
    coinbase.renew_coinbase(port)

"""
General Functions
"""


def db_commit_directly(item) -> None:
    db.session.add(item)
    db.session.commit()


def check_int(str_int: str, lower_bound_check=True) -> int:
    # Function checks if a string converts to an integer, returns said integer otherwise throws ValueError
    try:
        true_int = int(str_int)
    except ValueError:
        raise ValueError("amount is not an integer")

    if true_int <= 0 and lower_bound_check:
        raise ValueError("amount to send cannot be less than 0")

    return true_int


def check_uuid(str_uuid: str) -> uuid:
    # Function checks if a string coverts to a uuid, returns said uuid otherwise throws ValueError
    try:
        uuidv4 = uuid.UUID(str_uuid)
    except ValueError:
        raise ValueError("Given UUID is not a valid UUID string")

    if uuidv4.version != 4:
        raise ValueError(f"Invalid UUID version, expected version 4, received ${uuidv4.version}")

    return uuidv4


def check_public_key(key: str) -> RSAPublicKey:
    # Function checks if a string representation of a RSA public key and returns said key otherwise throws ValueError
    try:
        return crypto.ascii_key_to_public_key(key)
    except ValueError:
        raise ValueError("Given Public key could not be serialized")
    except (TypeError, cryptography.exceptions.UnsupportedAlgorithm) as e:
        raise ValueError(str(e))


def check_private_key(key: str) -> RSAPrivateKey:
    # Function checks if a string representation of a RSA public key and returns said key otherwise throws ValueError
    try:
        return crypto.ascii_key_to_private_key(key)
    except ValueError:
        raise ValueError("Given Private key could not be serialized")
    except (TypeError, cryptography.exceptions.UnsupportedAlgorithm) as e:
        raise ValueError(str(e))


class CheckTransReturn:
    # A storage container class just for transaction requests
    # Simply stores common information for transaction requests

    def __init__(self, sender_public_key: RSAPublicKey, sender_private_key: Union[None, RSAPrivateKey],
                 recipient_public_key: RSAPublicKey, amount: int, uuidv4: uuid.UUID, signature: str):
        self.sender_public_key = sender_public_key
        self.sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.uuidv4 = uuidv4
        self.signature = signature


def check_transaction_request(json_request: dict, check_private_key_flag: bool = False,
                              check_signature: bool = False) -> CheckTransReturn:
    # Function takes a json request object(typically from flask) and
    # checks if it has common fields for transaction requests; Returns a storage class

    if json_request is None:
        raise RuntimeError("Missing JSON POST request data")

    # Get all possible requirements
    sender_public_key = check_public_key(json_request["sender_public_key"])
    sender_private_key = check_private_key(json_request["sender_private_key"]) if check_private_key_flag else None
    recipient_public_key = check_public_key(json_request["recipient_public_key"])
    amount = check_int(json_request["amount"])
    uuidv4 = check_uuid(json_request["uuid"])
    signature = json_request["signature"]

    # Missing Values Checking
    requirements = [sender_public_key, recipient_public_key, amount, uuidv4]
    if check_signature:
        requirements.append(signature)
    if check_private_key_flag:
        requirements.append(sender_private_key)

    if [None, ""] in requirements:
        raise ValueError("A field is missing")

    return CheckTransReturn(sender_public_key, sender_private_key, recipient_public_key, amount, uuidv4, signature)


"""
Endpoints
"""


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/wallet", methods=["GET"])
def create_new_wallet():
    # Endpoint creates a new wallet by providing returning a new public/private RSA key pair
    # Note that typically in a coinbase, the coinbase wouldn't be doing this, but this provides the option
    wallet = crypto.Wallet()
    private_key, public_key = wallet.keys_to_ascii()
    response = {
        "private_key": private_key,
        "public_key": public_key
    }
    return response


@app.route("/api/wallet/balance", methods=["GET"])
def check_wallet_balance():
    # Endpoint determines a wallet's balance, given a public key

    # Query string checking
    query_strings = request.args
    if "public_key" not in query_strings:
        return "Missing public key", 400

    # string conversion
    try:
        public_key = check_public_key(query_strings["public_key"])
    except ValueError as e:
        return str(e), 400

    # get balance
    return str(CoinBase.get_key_balance(public_key)), 200


@app.route("/api/transaction/sign", methods=["POST"])
def sign_transaction():
    # Endpoint for allowing for signing a transaction
    # Similarly to gen wallets we provide the option, the coinbase should not really have these.

    # Check all inputs to verify
    try:
        json_post = check_transaction_request(request.json, check_private_key_flag=True)
    except Exception as e:
        return str(e), 400

    # From those inputs create a new transaction and sign it
    transaction = Transaction(json_post.sender_public_key,
                              json_post.sender_private_key,
                              json_post.recipient_public_key,
                              json_post.amount,
                              json_post.uuidv4)
    transaction.sign()

    # Give back the transaction, but with the signature
    response = transaction.to_ascii_dict()
    response["signature"] = crypto.binary_to_ascii(transaction.signature)

    return jsonify(response), 200


@app.route("/api/transaction", methods=["POST"])
def generate_transaction():
    # Endpoint generates a new transaction and stores it on this node

    # Verify all inputs
    try:
        json_post = check_transaction_request(request.json, check_signature=True)
    except Exception as e:
        return str(e), 400

    # Store them into a transaction object
    transaction = Transaction(json_post.sender_public_key,
                              None,
                              json_post.recipient_public_key,
                              json_post.amount,
                              json_post.uuidv4)
    transaction.signature = crypto.ascii_to_binary(json_post.signature)

    # ensure that the transaction is valid and then return
    if not transaction.is_valid():
        return "Transaction Signature is not valid", 400

    db_commit_directly(transaction)
    # blockchain.transactions.append(transaction)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route("/api/transaction/<uuid:transaction_uuid>", methods=["GET"])
def get_transaction(transaction_uuid: uuid):
    # Endpoint finds a match for a given uuid and gives back the transaction
    trans = Transaction.query.filter_by(uuid=transaction_uuid).one_or_none()
    if trans is None:
        return "{}", 200
    return json.dumps(trans, default=crypto.serializer), 200


@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    # Endpoint GET returns all transaction in this coinbase
    return json.dumps(Transaction.query.filter_by(has_been_mined=False).all(), default=crypto.serializer), 200


@app.route("/api/mine", methods=["GET", "POST"])
def mine():
    # Endpoint GET returns all minable blocks that the client is able to mine
    # Endpoint POST expects a block in binary in form [miner's public key]|[block's mining input]|[proof of work]
    # and adds it to the blockchain

    if request.method == "GET":
        blockchain.create_mining_blocks()  # Create mining blocks if needed
        # Give the mining blocks in the mining input format
        return json.dumps(
            {"blocks": [{"uuid": block.uuid,
                         "block": block.get_mining_input()}
                        for block in Block.query.filter_by(is_mining_block=True).all()]},
            default=crypto.serializer
        ), 200

    miner_public_key = request.json["miner_public_key"]  # we allow string type for the key here
    # Check/Verify inputs
    try:
        proof_of_work = check_int(request.json["proof_of_work"])
        block_uuid = check_uuid(request.json["uuid"])
        check_public_key(miner_public_key)
    except ValueError as e:
        return str(e), 400

    if [None, ""] in [block_uuid, miner_public_key, proof_of_work]:
        return "Missing POST values", 400

    # Find the block the miner specified
    error_find_block_msg, fatal_error, block = blockchain.find_mine_block(block_uuid)

    if block is None:
        return error_find_block_msg, 400 if fatal_error else 401

    # Try this proof of work the miner sent and see if this works
    error_proof_msg = block.check_proof_of_work(proof_of_work, miner_public_key)

    if error_proof_msg:
        return error_proof_msg, 400

    # Checks out, now we need to add the transaction to the blockchain and remove it from minable block
    blockchain.move_minable_block(block)

    # We have to regenerate the mining blocks now, the previous block hash is now this one
    blockchain.clear_mining_blocks()

    # Lastly, reward the miner!
    # This is actually implicit, since the block is in the chain, the coinbase logged the user of mining that block,
    # Thus from the server's standpoint they been rewarded crypto.block_mining_reward
    # for their address simply being there.
    return f"Miner received {crypto.block_mining_reward} coins for Block UUID {block_uuid}", 200


@app.route("/api/mine/numzeros", methods=["GET"])
def give_number_of_zeros():
    # Endpoint returns the number of zeros of a mining block's SHA256 hash that must be at the start for it to count as
    # a valid proof of work
    return str(crypto.num_of_zeros), 200


@app.route("/api/chain", methods=["GET"])
def get_chain():
    # Endpoint returns the blocks in the blockchain

    # Support for filtering with query strings
    # Parse and put the query strings into variables
    query_strings = request.args
    miner_key = block_index = block_uuid = None

    try:
        if "miner_key" in query_strings:
            miner_key = check_public_key(query_strings["miner_key"])

        if "block_index" in query_strings:
            block_index = check_int(query_strings["block_index"], lower_bound_check=False)

        if "block_uuid" in query_strings:
            block_uuid = check_uuid(query_strings["block_uuid"])
    except ValueError as e:
        return str(e), 400

    # Now apply all filters onto the query, if supplied
    chain = Block.query.filter_by(is_mining_block=False)
    if miner_key is not None:
        chain = chain.filter_by(miner_key=miner_key)
    if block_index is not None:
        if block_index == -1:
            chain = chain.filter_by(index=db.session.query(func.max(Block.index)).scalar())
        else:
            chain = chain.filter_by(index=block_index)
    if block_uuid is not None:
        chain = chain.filter_by(uuid=block_uuid)

    chain = chain.all()
    return json.dumps({
        "blocks":
            [{
                "index": block.index,
                "uuid": block.uuid,
                "hash": block.block_hash,
                "proof_of_work": block.proof_of_work,
                "previous_hash": block.previous_block_hash,
                "miner_key": crypto.public_key_to_ascii_key(block.miner_key) if block.miner_key is not None else "",
                "transactions": [trans.to_ascii_dict(include_signature=True) for trans in block.transactions]
            }
                for block in chain]
    }, default=crypto.serializer), 200


@app.route("/api/buy", methods=["POST"])
def buy_coins():
    # Endpoint gives (free) coins to the user

    # Get data from json supplied data
    json_request = request.json
    try:
        if json_request is None:
            raise ValueError("Missing json data")

        public_key = check_public_key(json_request["public_key"])
        if "amount" not in json_request:
            amount = 10
        else:
            amount = check_int(json_request["amount"])
    except ValueError as e:
        return str(e), 400

    # Create a brand new transaction
    coinbase.give_key_coins(public_key, amount)
    return f"{public_key} received {amount} coins", 200


if __name__ == '__main__':
    app.run(debug=True, port=port)

import json
import uuid
import blockchain as crypto

from flask import Flask, jsonify, request, render_template
from blockchain import Wallet, Transaction, BlockChain

app = Flask(__name__)
blockchain = BlockChain()

"""
General Functions
"""


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


class CheckTransReturn:
    # A storage container class just for transaction requests
    # Simply stores common information for transaction requests

    # TODO force keys to be of RSA public/private key type
    def __init__(self, sender_public_key: str, sender_private_key: str,
                 recipient_public_key: str, amount: int, uuidv4: uuid.UUID, signature: str):
        self.sender_public_key = sender_public_key
        self.sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.uuidv4 = uuidv4
        self.signature = signature


def check_transaction_request(json_request: dict, check_private_key: bool = False,
                              check_signature: bool = False) -> CheckTransReturn:
    # Function takes a json request object(typically from flask) and
    # checks if it has common fields for transaction requests; Returns a storage class

    if json_request is None:
        raise RuntimeError("Missing JSON POST request data")

    # Get all possible requirements
    sender_public_key = json_request["sender_public_key"]
    sender_private_key = json_request["sender_private_key"]
    recipient_public_key = json_request["recipient_public_key"]
    amount = check_int(json_request["amount"])
    uuidv4 = check_uuid(json_request["uuid"])
    signature = json_request["signature"]

    # Missing Values Checking
    requirements = [sender_public_key, recipient_public_key, amount, uuidv4]
    if check_signature:
        requirements.append(signature)
    if check_private_key:
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


@app.route("/api/transaction/sign", methods=["POST"])
def sign_transaction():
    # Endpoint for allowing for signing a transaction
    # Similarly to gen wallets we provide the option, the coinbase should not really have these.

    # Check all inputs to verify
    try:
        json_post = check_transaction_request(request.json, check_private_key=True)
    except Exception as e:
        return str(e), 400

    # From those inputs create a new transaction and sign it
    wallet = Wallet.from_ascii_keys(json_post.sender_private_key, json_post.sender_public_key)
    transaction = Transaction(wallet.public_key,
                              wallet.private_key,
                              crypto.ascii_key_to_public_key(json_post.recipient_public_key),
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
    transaction = Transaction(crypto.ascii_key_to_public_key(json_post.sender_public_key),
                              None,
                              crypto.ascii_key_to_public_key(json_post.recipient_public_key),
                              json_post.amount,
                              json_post.uuidv4)
    transaction.signature = crypto.ascii_to_binary(json_post.signature)

    # ensure that the transaction is valid and then return
    if not transaction.is_valid():
        return "Transaction Signature is not valid", 400

    blockchain.transactions.append(transaction)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route("/api/transaction/<uuid:transaction_uuid>", methods=["GET"])
def get_transaction(transaction_uuid: uuid):
    # Endpoint finds a match for a given uuid and gives back the transaction

    matches = [trans for trans in blockchain.transactions if trans.uuid == transaction_uuid]

    if len(matches) == 0:
        return "{}", 200
    elif len(matches) > 1:
        print(f"FATAL: Multiple uuids detected in a blockchain with uuid ${transaction_uuid}")

    return json.dumps(matches[0], default=crypto.serializer), 200


@app.route("/api/transactions", methods=["GET", "POST"])
def get_transactions():
    # Endpoint GET returns all transaction in this coinbase
    # Endpoint POST returns all transactions in this coinbase that matches the uuid given from the client

    if request.method == "GET":
        return json.dumps(blockchain.transactions, default=crypto.serializer), 200

    if request.json is None or request.json["uuids"] is None:
        return "{}", 200

    # Give matching transaction uuids
    return json.dumps(
        [transaction for transaction in blockchain.transactions if str(transaction.uuid) in request.json["uuids"]],
        default=crypto.serializer
    ), 200


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
                        for block in blockchain.minable_blocks]},
            default=crypto.serializer
        ), 200

    # Check/Verify inputs
    miner_public_key = request.json["miner_public_key"]

    try:
        proof_of_work = check_int(request.json["proof_of_work"])
        block_uuid = check_uuid(request.json["uuid"])
    except ValueError as e:
        return str(e), 400

    if [None, ""] in [block_uuid, miner_public_key, proof_of_work]:
        return "Missing POST values", 400

    # Find the block the miner specified
    error_find_block_msg, block = blockchain.find_mine_block(block_uuid)

    if error_find_block_msg:
        return error_find_block_msg, 400

    # Try this proof of work the miner sent and see if this works
    error_proof_msg = block.check_proof_of_work(proof_of_work, miner_public_key)

    if error_proof_msg:
        return error_proof_msg, 400

    # Checks out, now we need to add the transaction to the blockchain and remove it from minable block
    move_error = blockchain.move_minable_block(block)
    if move_error:
        return move_error, 500

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
    return jsonify(blockchain.chain), 200


if __name__ == '__main__':
    app.run(debug=True)

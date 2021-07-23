import json
import uuid

from flask import Flask, jsonify, request, render_template
from blockchain import Wallet, Transaction, BlockChain
import blockchain as crypto
from uuid import uuid4

app = Flask(__name__)
blockchain = BlockChain()


@app.route("/")
def home():
    return render_template("index.html")


# Endpoint creates a new wallet by providing returning a new public/private RSA key pair
@app.route("/api/wallet", methods=["GET"])
def create_new_wallet():
    wallet = crypto.Wallet()
    private_key, public_key = wallet.keys_to_ascii()
    response = {
        "private_key": private_key,
        "public_key": public_key
    }
    return response


def check_int(str_int: str) -> int:
    try:
        true_int = int(str_int)
    except ValueError:
        raise ValueError("amount is not an integer")
    if true_int <= 0:
        raise ValueError("amount to send cannot be less than 0")
    return true_int


def check_uuid(str_uuid: str) -> uuid:
    # UUIDV4 Checking
    try:
        uuidv4 = uuid.UUID(str_uuid)
    except ValueError as ve:
        raise ValueError("Given UUID is not a valid UUID string")

    if uuidv4.version != 4:
        raise ValueError(f"Invalid UUID version, expected version 4, received ${uuidv4.version}")

    return uuidv4


class CheckTransReturn:
    def __init__(self, sender_public_key, sender_private_key, recipient_public_key, amount, uuidv4, signature):
        self.sender_public_key = sender_public_key
        self.sender_private_key = sender_private_key
        self.recipient_public_key = recipient_public_key
        self.amount = amount
        self.uuidv4 = uuidv4
        self.signature = signature


def check_transaction_request(json_request, check_private_key=False, check_signature=False) -> CheckTransReturn:
    if json_request is None:
        raise RuntimeError("Missing JSON POST request data")

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


# Allows for signing a transaction
# Our server automatically assigns UUIDs to a transaction to prevent copying
@app.route("/api/transaction/sign", methods=["POST"])
def sign_transaction():
    json_post = None
    try:
        json_post = check_transaction_request(request.json, check_private_key=True)
    except Exception as e:
        return str(e), 400

    wallet = Wallet.from_ascii_keys(json_post.sender_private_key, json_post.sender_public_key)
    transaction = Transaction(wallet.public_key,
                              wallet.private_key,
                              crypto.ascii_key_to_public_key(json_post.recipient_public_key),
                              json_post.amount,
                              json_post.uuidv4)
    transaction.sign()

    response = transaction.to_ascii_dict()
    response["signature"] = crypto.binary_to_ascii(transaction.signature)

    return jsonify(response), 200


# Generates a new transaction and stores it on this node
@app.route("/api/transaction", methods=["POST"])
def generate_transaction():
    json_post = None
    try:
        json_post = check_transaction_request(request.json, check_signature=True)
    except Exception as e:
        return str(e), 400

    transaction = Transaction(crypto.ascii_key_to_public_key(json_post.sender_public_key),
                              None,
                              crypto.ascii_key_to_public_key(json_post.recipient_public_key),
                              json_post.amount,
                              json_post.uuidv4)
    transaction.signature = crypto.ascii_to_binary(json_post.signature)

    if not transaction.is_valid():
        return "Transaction Signature is not valid", 400

    blockchain.transactions.append(transaction)

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@app.route("/api/transaction/<uuid:transaction_uuid>", methods=["GET"])
def get_transaction(transaction_uuid):
    matches = [trans for trans in blockchain.transactions if trans.uuid == transaction_uuid]
    if len(matches) == 0:
        return "{}", 200
    elif len(matches) > 1:
        print(f"FATAL: Multiple uuids detected in a blockchain with uuid ${transaction_uuid}")

    return json.dumps(matches[0], default=crypto.serializer), 200


@app.route("/api/transactions", methods=["GET", "POST"])
def get_transactions():
    if request.method == "GET":
        return json.dumps(blockchain.transactions, default=crypto.serializer), 200

    if request.json is None or request.json["uuids"] is None:
        return "{}", 200

    return json.dumps(
        [transaction for transaction in blockchain.transactions if str(transaction.uuid) in request.json["uuids"]],
        default=crypto.serializer
    ), 200


@app.route("/api/mine", methods=["GET", "POST"])
def mine():
    if request.method == "GET":
        blockchain.create_block()
        b = blockchain.minable_blocks[0]
        print("Hash BEF:" + b.hash(False))
        print("Hash BEFw/t: " + b.hash(True))
        b.proof_of_work = 100
        print("Hash AFT: " + b.hash())
        return json.dumps(
            {"blocks": [block.get_mining_input() for block in blockchain.minable_blocks]},
            default=crypto.serializer
        ), 200

    miner_public_key = request.json["miner_public_key"]

    try:
        proof_of_work = check_int(request.json["proof_of_work"])
        block_uuid = check_uuid(request.json["uuid"])
    except ValueError as e:
        return str(e), 400

    if [None, ""] in [block_uuid, miner_public_key, proof_of_work]:
        return "Missing POST values", 400

    error_find_block_msg, block = blockchain.find_mine_block(block_uuid)

    if error_find_block_msg:
        return error_find_block_msg, 400

    # Try this proof of work the miner sent and see if this works
    error_proof_msg = block.check_proof_of_work(proof_of_work)

    if error_proof_msg:
        return error_proof_msg, 400

    # Checks out, now we need to add the transaction to the blockchain and remove it from minable block
    move_error = blockchain.move_minable_block(block)
    if move_error:
        return move_error, 400

    # Lastly, reward the miner!



@app.route("/api/chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain.chain), 200


if __name__ == '__main__':
    app.run(debug=True)

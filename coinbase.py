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
    amount = json_request["amount"]
    uuidv4 = json_request["uuid"]
    signature = json_request["signature"]

    # UUIDV4 Checking
    try:
        uuidv4 = uuid.UUID(uuidv4)
    except ValueError as ve:
        raise ValueError("Given UUID is not a valid UUID string")

    if uuidv4.version != 4:
        raise ValueError(f"Invalid UUID version, expected version 4, received ${uuidv4.version}")

    # Amount Checking
    try:
        amount = int(amount)
    except ValueError:
        raise ValueError("amount is not an integer")
    if amount <= 0:
        raise ValueError("amount to send cannot be less than 0")

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
    blockchain.create_block()
    return json.dumps(
        blockchain.minable_blocks,
        default=crypto.serializer
    ), 200


@app.route("/api/chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain.chain), 200


if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, jsonify, request
from blockchain import Wallet, Transaction, BlockChain
import blockchain as crypto
import json

app = Flask(__name__)

blockchain = BlockChain()


# Endpoint creates a new wallet by providing returning a new public/private RSA key pair
@app.route("/api/wallet/new", methods=["GET"])
def create_new_wallet():
    wallet = crypto.Wallet()
    private_key, public_key = wallet.keys_to_ascii()
    response = {
        "private_key": private_key,
        "public_key": public_key
    }
    return jsonify(response), 200


# Generates a new transaction
@app.route("/api/transaction/new", methods=["POST"])
def generate_transaction():
    json_req = request.json
    if json_req is None:
        return "Missing JSON POST request data", 400

    sender_public_key = json_req["sender_public_key"]
    sender_private_key = json_req["sender_private_key"]
    recipient_public_key = json_req["recipient_public_key"]
    amount = json_req["amount"]

    wallet = Wallet.from_ascii_keys(sender_private_key, sender_public_key)
    transaction = Transaction(wallet.public_key, wallet.private_key,
                              crypto.ascii_key_to_public_key(recipient_public_key), amount)
    transaction.sign()
    response = {
        "transaction": transaction.to_ascii_dict(),
        "signature": crypto.binary_to_ascii(transaction.signature)
    }
    # Important to not store the private key of the sender to the blockchain
    transaction.sender_private_key = None
    blockchain.add_transaction(transaction)

    return jsonify(response), 200


@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    return jsonify(blockchain.transactions), 200


@app.route("/api/chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain.chain), 200


if __name__ == '__main__':
    app.run()

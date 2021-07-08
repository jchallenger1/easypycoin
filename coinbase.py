from flask import Flask, jsonify, request
import blockchain
import json

app = Flask(__name__)


# Endpoint creates a new wallet by providing returning a new public/private RSA key pair
@app.route("/api/wallet/new", methods=["GET"])
def create_new_wallet():
    wallet = blockchain.Wallet()
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
    wallet = blockchain.Wallet.from_ascii_keys(sender_private_key, sender_public_key)

    transaction = blockchain.Transaction(wallet.public_key, wallet.private_key, recipient_public_key, amount)
    response = {
        "transaction": transaction.to_dict(),
        "signature": transaction.sign()
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run()

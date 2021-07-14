from flask import Flask, jsonify, request, render_template
from blockchain import Wallet, Transaction, BlockChain
import blockchain as crypto

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


# Allows for signing a transaction
@app.route("/api/transaction/sign", methods=["POST"])
def sign_transaction():
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

    return jsonify(response), 200


# Generates a new transaction and stores it on this node
@app.route("/api/transaction", methods=["POST"])
def generate_transaction():
    json_req = request.json
    if json_req is None:
        return "Missing JSON POST request data", 400

    json_trans = json_req["transaction"]
    signature = json_req["signature"]

    transaction = Transaction(json_trans["sender_public_key"], None,
                              json_trans["recipient_public_key"], json_trans["amount"])
    transaction.signature = crypto.ascii_to_binary(signature)

    if not transaction.is_valid():
        return "Transaction is not valid", 400

    blockchain.transactions.append(transaction)


@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    return jsonify(blockchain.transactions), 200


@app.route("/api/chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain.chain), 200


if __name__ == '__main__':
    app.run(debug=True)

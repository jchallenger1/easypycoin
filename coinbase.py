from flask import Flask, jsonify, request
import blockchain as bc

app = Flask(__name__)


@app.route("/api/wallet/new", methods=["GET"])
def create_new_wallet():
    wallet = bc.Wallet()
    private_key, public_key = wallet.keys_to_ascii()
    response = {
        "private_key": private_key,
        "public_key": public_key
    }
    return jsonify(response), 200


@app.route("/api/generate/transaction", methods=["POST"])
def generate_transaction():
    sender_public_key = request.form["sender_public_key"]
    sender_private_key = request.form["sender_private_key"]
    recipient_public_key = request.form["recipient_public_key"]
    amount = request.form["amount"]
    wallet = bc.Wallet(sender_private_key, sender_public_key)

    transaction = bc.Transaction(wallet.public_key, wallet.private_key, recipient_public_key, amount)
    response = {
        "transaction": transaction.to_dict(),
        "signature": transaction.sign()
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run()

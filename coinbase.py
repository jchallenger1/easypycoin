from flask import Flask, jsonify
from blockchain import Wallet

app = Flask(__name__)


@app.route("/api/wallet/new", methods=["GET"])
def create_new_wallet():
    wallet = Wallet()
    private_key, public_key = wallet.keys_to_ascii()
    print(private_key)
    print(public_key)
    print(wallet.keys_to_bytes()[0])
    response = {
        "private_key": private_key,
        "public_key": public_key
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run()

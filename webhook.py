from flask import Flask, request
import secrets

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("Webhookを受信しました")

    # Stripeの購入情報
    session = data["data"]["object"]

    # ランダムなチケットIDを生成
    ticket_id = "TKT-" + secrets.token_hex(8).upper()

    print("購入金額:", session["amount_total"], "円")
    print("決済状態:", session["payment_status"])
    print("チケットID:", ticket_id)

    return "OK", 200

@app.route("/")
def home():
    return "Webhook server is running"

from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    print("Webhookを受信しました")
    print(request.json)
    return "OK", 200

@app.route("/")
def home():
    return "Webhook server is running"


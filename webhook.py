from flask import Flask, request
import secrets
import os
import psycopg2

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("Webhookを受信しました")

    # Stripeの購入情報
    session = data["data"]["object"]

    # チケットIDを生成
    ticket_id = "TKT-" + secrets.token_hex(8).upper()

    # PostgreSQLへ接続
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    # ticketsテーブルを作成（存在しない場合）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id SERIAL PRIMARY KEY,
            ticket_type VARCHAR(100) NOT NULL,
            issue_number INTEGER NOT NULL,
            ticket_id VARCHAR(100) NOT NULL UNIQUE,
            purchaser_name VARCHAR(200),
            amount INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # チケット情報をDBへ保存
    cur.execute("""
        INSERT INTO tickets (
            ticket_type,
            issue_number,
            ticket_id,
            purchaser_name,
            amount
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        "ライブチケット",
        1,
        ticket_id,
        session.get("customer_details", {}).get("name"),
        session["amount_total"]
    ))

    conn.commit()

    print("チケットをDBに保存しました")

    # DBに保存された最新のチケットを確認
    cur.execute("""
        SELECT ticket_type, issue_number, ticket_id, purchaser_name, amount
        FROM tickets
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    print("DBの最新チケット:", row)

    cur.close()
    conn.close()

    print("購入金額:", session["amount_total"], "円")
    print("決済状態:", session["payment_status"])
    print("チケットID:", ticket_id)

    return "OK", 200


@app.route("/")
def home():
    return "Webhook server is running"

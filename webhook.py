from flask import Flask, request
import secrets
import os
import psycopg2
import stripe

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("Webhookを受信しました")

    # Stripeの購入情報
    session = data["data"]["object"]

    # Stripe APIの認証
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

    # Stripeから購入商品の情報を取得
    line_items = stripe.checkout.Session.list_line_items(
        session["id"]
    )

    for item in line_items.data:
        print("商品数量:", item.quantity)

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

    # チケットごとの連番管理テーブルを作成
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_counters (
            ticket_type VARCHAR(100) PRIMARY KEY,
            next_number INTEGER NOT NULL
        )
    """)

    # チケットの連番を取得
    cur.execute("""
        INSERT INTO ticket_counters (ticket_type, next_number)
        VALUES (%s, 2)
        ON CONFLICT (ticket_type)
        DO UPDATE SET next_number = ticket_counters.next_number + 1
        RETURNING next_number
    """, ("ライブチケット",))

    next_number = cur.fetchone()[0]

    issue_number = next_number - 1

    print("発行番号:", issue_number)

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
        issue_number,
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

# DB初期化
@app.route("/reset-db")
def reset_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS tickets")
    cur.execute("DROP TABLE IF EXISTS ticket_counters")

    conn.commit()

    cur.close()
    conn.close()

    return "DBを初期化しました"

```python
from flask import Flask, request
import secrets
import os
import psycopg2
import stripe

app = Flask(__name__)

# Stripe API認証
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


@app.route("/webhook", methods=["POST"])
def webhook():

    # Stripe Webhookの署名を検証
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.environ["STRIPE_WEBHOOK_SECRET"]
        )

    except ValueError:
        print("Webhookのデータが不正です")
        return "Invalid payload", 400

    except stripe.error.SignatureVerificationError:
        print("Webhookの署名が不正です")
        return "Invalid signature", 400

    # 検証済みのStripeイベントを取得
    data = event.to_dict()

    print("Webhookの署名検証に成功しました")
    print("Webhookを受信しました")

    # StripeイベントID
    event_id = data["id"]

    # Stripeの購入情報
    session = data["data"]["object"]

    # PostgreSQLへ接続
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    # Webhookの処理済みイベントを管理するテーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS webhook_events (
            event_id VARCHAR(255) PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # このWebhookを初めて処理するか確認
    cur.execute("""
        INSERT INTO webhook_events (event_id)
        VALUES (%s)
        ON CONFLICT (event_id) DO NOTHING
        RETURNING event_id
    """, (event_id,))

    new_event = cur.fetchone()

    # すでに処理済みなら何もしない
    if new_event is None:
        conn.rollback()
        cur.close()
        conn.close()

        print("このWebhookは処理済みです:", event_id)

        return "OK", 200

    print("新しいWebhookです:", event_id)

    # Stripeから購入商品の情報を取得
    line_items = stripe.checkout.Session.list_line_items(
        session["id"],
        expand=["data.price.product"]
    )

    # ticketsテーブルを作成
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

    # チケットごとの連番管理テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_counters (
            ticket_type VARCHAR(100) PRIMARY KEY,
            next_number INTEGER NOT NULL
        )
    """)

    # 商品ごとに処理
    for item in line_items.data:

        price_id = item.price.id
        quantity = item.quantity

        print("購入されたPrice ID:", price_id)
        print("購入数量:", quantity)

        # Stripeの商品を取得
        product = item.price.product

        # 商品メタデータからチケット種類を取得
        ticket_type = product.metadata.get("ticket_type")

        # ticket_typeが設定されていない商品
        if not ticket_type:
            print("ticket_typeが設定されていない商品です:", product.id)
            continue

        print("チケット種類:", ticket_type)

        # 数量分のチケットを発行
        for i in range(quantity):

            # チケット種類ごとの連番を取得
            cur.execute("""
                INSERT INTO ticket_counters (ticket_type, next_number)
                VALUES (%s, 2)
                ON CONFLICT (ticket_type)
                DO UPDATE SET next_number = ticket_counters.next_number + 1
                RETURNING next_number
            """, (ticket_type,))

            next_number = cur.fetchone()[0]

            issue_number = next_number - 1

            # チケットIDを生成
            ticket_id = "TKT-" + secrets.token_hex(8).upper()

            print("発行番号:", issue_number)
            print("チケットID:", ticket_id)

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
                ticket_type,
                issue_number,
                ticket_id,
                session.get("customer_details", {}).get("name"),
                item.amount_total // quantity
            ))

    # Webhook処理全体を確定
    conn.commit()

    print("チケットをDBに保存しました")

    # 今回発行されたチケットを確認
    cur.execute("""
        SELECT ticket_type, issue_number, ticket_id, purchaser_name, amount
        FROM tickets
        ORDER BY id DESC
        LIMIT 10
    """)

    rows = cur.fetchall()

    for row in reversed(rows):
        print("DBのチケット:", row)

    cur.close()
    conn.close()

    print("購入金額:", session["amount_total"], "円")
    print("決済状態:", session["payment_status"])

    return "OK", 200


@app.route("/")
def home():
    return "Webhook server is running"
```

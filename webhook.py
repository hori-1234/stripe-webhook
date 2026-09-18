from flask import Flask, request
import os
import psycopg2
import stripe

from ticket import issue_tickets

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

    try:

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

            print("このWebhookは処理済みです:", event_id)

            return "OK", 200

        print("新しいWebhookです:", event_id)

        # Stripeから購入商品の情報を取得
        line_items = stripe.checkout.Session.list_line_items(
            session["id"],
            expand=["data.price.product"]
        )

        # 現在はチケット処理を実行
        issue_tickets(
            cur,
            line_items,
            session
        )

        # Webhook処理全体を確定
        conn.commit()

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

        print("購入金額:", session["amount_total"], "円")
        print("決済状態:", session["payment_status"])

        return "OK", 200

    except Exception:
        conn.rollback()

        print("Webhook処理中にエラーが発生しました")

        raise

    finally:
        cur.close()
        conn.close()


@app.route("/")
def home():
    return "Webhook server is running"

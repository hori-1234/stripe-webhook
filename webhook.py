from flask import Flask, request
import os
import psycopg2
import stripe
import resend
from types import SimpleNamespace

from ticket import issue_tickets
from goods import save_goods
from mail import send_ticket_email

app = Flask(__name__)

# Stripe API認証
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

# Resend API認証
resend.api_key = os.environ["RESEND_API_KEY"]


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

        # チケットと物販を分ける
        ticket_items = []
        goods_items = []

        for item in line_items.data:

            product = item.price.product

            metadata = product.metadata.to_dict()

            product_type = metadata.get("product_type")

            print("商品名:", product.name)
            print("product_type:", product_type)

            if product_type == "ticket":
                ticket_items.append(item)

            elif product_type == "goods":
                goods_items.append(item)

            else:
                print(
                    "product_typeが設定されていない商品です:",
                    product.id
                )

        # 発行されたチケットを保持
        issued_tickets = []

        # チケット処理
        if ticket_items:

            print("チケット処理を開始します")

            ticket_line_items = SimpleNamespace(
                data=ticket_items
            )

            issued_tickets = issue_tickets(
                cur,
                ticket_line_items,
                session
            )

            print(
                "発行されたチケット数:",
                len(issued_tickets)
            )

            for ticket in issued_tickets:

                print(
                    "発行チケット:",
                    ticket["ticket_type"],
                    ticket["issue_number"],
                    ticket["ticket_id"]
                )

        # 物販処理
        if goods_items:

            print("物販処理を開始します")

            goods_line_items = SimpleNamespace(
                data=goods_items
            )

            save_goods(
                cur,
                goods_line_items,
                session
            )

        # Webhook処理全体を確定
        conn.commit()

        # チケットメール送信
        if issued_tickets:

            print("チケットメール送信を開始します")

            send_ticket_email(
                session,
                issued_tickets
            )

        # 今回発行されたチケットを確認
        cur.execute("""
            SELECT ticket_type, issue_number, ticket_id, purchaser_name, amount
            FROM tickets
            ORDER BY id DESC
            LIMIT 10
        """)

        rows = cur.fetchall()

        for row in reversed(rows):

            print(
                "DBのチケット:",
                row
            )

        print(
            "購入金額:",
            session["amount_total"],
            "円"
        )

        print(
            "決済状態:",
            session["payment_status"]
        )

        return "OK", 200

    except Exception:

        conn.rollback()

        print(
            "Webhook処理中にエラーが発生しました"
        )

        raise

    finally:

        cur.close()
        conn.close()


# Resendテストメール
@app.route("/test-email")
def test_email():

    try:

        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": ["delivered@resend.dev"],
            "subject": "マイマケ テストメール",
            "text": "Resendからのテストメールです。"
        })

        print(
            "テストメール送信成功:",
            response
        )

        return "テストメール送信成功"

    except Exception as e:

        print(
            "テストメール送信失敗:",
            e
        )

        return "テストメール送信失敗", 500


@app.route("/")
def home():

    return "Webhook server is running"

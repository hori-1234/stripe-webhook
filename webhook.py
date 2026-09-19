from flask import Flask, request
import os
import psycopg2
import stripe
import resend

from product import process_products
from ticket_check import check_ticket


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

    # 検証済みのStripeイベント
    data = event.to_dict()

    print("Webhookの署名検証に成功しました")
    print("Webhookを受信しました")

    # StripeイベントID
    event_id = data["id"]

    # Stripe Checkout Session
    session = data["data"]["object"]

    # PostgreSQLへ接続
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        # Webhook処理済みイベント管理
        cur.execute("""
            CREATE TABLE IF NOT EXISTS webhook_events (
                event_id VARCHAR(255) PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 初回Webhookか確認
        cur.execute("""
            INSERT INTO webhook_events (event_id)
            VALUES (%s)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id
        """, (event_id,))

        new_event = cur.fetchone()

        # すでに処理済み
        if new_event is None:

            conn.rollback()

            print(
                "このWebhookは処理済みです:",
                event_id
            )

            return "OK", 200

        print(
            "新しいWebhookです:",
            event_id
        )

        # Stripeから購入商品の情報を取得
        line_items = stripe.checkout.Session.list_line_items(
            session["id"],
            expand=["data.price.product"]
        )

        # 商品処理をproduct.pyへ渡す
        issued_tickets = process_products(
            cur,
            line_items,
            session
        )

        # DB処理を確定
        conn.commit()

        # チケットが発行された場合
        # ticket.py側から返されたチケット情報を
        # mail.pyへ渡す
        if issued_tickets:

            from mail import send_ticket_email

            print(
                "チケットメール送信を開始します"
            )

            send_ticket_email(
                session,
                issued_tickets
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


# QR・チケット確認
@app.route("/ticket/<ticket_id>")
def ticket_check(ticket_id):

    return check_ticket(ticket_id)

@app.route("/ticket/<ticket_id>/use", methods=["POST"])
def ticket_use(ticket_id):

    from ticket_check import use_ticket

    return use_ticket(ticket_id)

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

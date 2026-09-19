from flask import Flask, request
import os
import psycopg2
import stripe
import resend

from product import process_products
from ticket_check import check_ticket


app = Flask(__name__)

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
resend.api_key = os.environ["RESEND_API_KEY"]


@app.route("/webhook", methods=["POST"])
def webhook():

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:

        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            os.environ["STRIPE_WEBHOOK_SECRET"]
        )

    except ValueError:

        print(
            "Webhookのデータが不正です"
        )

        return "Invalid payload", 400

    except stripe.error.SignatureVerificationError:

        print(
            "Webhookの署名が不正です"
        )

        return "Invalid signature", 400

    data = event.to_dict()

    print(
        "Webhookの署名検証に成功しました"
    )

    print(
        "Webhookを受信しました"
    )

    event_id = data["id"]
    session = data["data"]["object"]

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            CREATE TABLE IF NOT EXISTS webhook_events (
                event_id VARCHAR(255) PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            INSERT INTO webhook_events (event_id)
            VALUES (%s)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id
        """, (event_id,))

        new_event = cur.fetchone()

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

        line_items = stripe.checkout.Session.list_line_items(
            session["id"],
            expand=["data.price.product"]
        )

        # 商品タイプを確認
        ticket_items = []
        goods_items = []

        for item in line_items.data:

            product = item.price.product

            metadata = product.metadata.to_dict()

            product_type = metadata.get("product_type")

            print(
                "商品名:",
                product.name
            )

            print(
                "product_type:",
                product_type
            )

            if product_type == "ticket":

                ticket_items.append(item)

            elif product_type == "goods":

                goods_items.append(item)

            else:

                print(
                    "product_typeが設定されていない商品です:",
                    product.id
                )

        # 商品処理
        issued_tickets = process_products(
            cur,
            line_items,
            session
        )

        # DB処理を確定
        conn.commit()

        # チケットメール
        if issued_tickets:

            from mail_ticket import send_ticket_email

            print(
                "チケットメール送信を開始します"
            )

            send_ticket_email(
                session,
                issued_tickets
            )

        # 物販メール
        if goods_items:

            from mail_goods import send_goods_email

            print(
                "物販購入確認メール送信を開始します"
            )

            send_goods_email(
                session,
                goods_items
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


@app.route("/ticket/<ticket_id>")
def ticket_check(ticket_id):

    return check_ticket(ticket_id)


@app.route("/ticket/<ticket_id>/use", methods=["POST"])
def ticket_use(ticket_id):

    from ticket_check import confirm_use_ticket

    return confirm_use_ticket(ticket_id)


@app.route("/ticket/<ticket_id>/confirm-use", methods=["POST"])
def ticket_confirm_use(ticket_id):

    from ticket_check import use_ticket

    return use_ticket(ticket_id)

@app.route("/ticket/<ticket_id>/cancel")
def ticket_cancel_request(ticket_id):

    from ticket_check import cancel_ticket_request

    return cancel_ticket_request(ticket_id)

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

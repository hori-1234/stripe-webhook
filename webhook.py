from flask import Flask, request, render_template_string
import os
import boto3
import psycopg2
import stripe
import resend


from product import process_products
from admin_auth import admin_required
from admin_export import export_excel
from ticket_check import (
    check_ticket,
    cancel_ticket_request,
    cancel_ticket_send,
    cancel_ticket_confirm
)


app = Flask(__name__)


r2 = boto3.client(
    "s3",
    endpoint_url=os.environ["R2_ENDPOINT"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"]
)

R2_BUCKET = os.environ["R2_BUCKET_NAME"]


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

    print(
        "Stripeカスタムフィールド:",
        session.get("custom_fields")
    )
    
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

        ticket_items = []
        goods_items = []
        digital_goods_items = []

        for item in line_items.data:

            product = item.price.product

            metadata = product.metadata.to_dict()

            product_type = metadata.get("product_type")
            goods_type = metadata.get("goods_type")

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

                if goods_type == "物販　PDF":

                    digital_goods_items.append(item)

                else:

                    goods_items.append(item)

            else:

                print(
                    "product_typeが設定されていない商品です:",
                    product.id
                )

        issued_tickets = process_products(
            cur,
            line_items,
            session
        )

        conn.commit()

        if issued_tickets:

            from mail_ticket import send_ticket_email

            print(
                "チケットメール送信を開始します"
            )

            send_ticket_email(
                session,
                issued_tickets
            )

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

    return cancel_ticket_request(ticket_id)


@app.route("/ticket/<ticket_id>/cancel-send", methods=["POST"])
def ticket_cancel_send(ticket_id):

    return cancel_ticket_send(ticket_id)


@app.route(
    "/ticket/<ticket_id>/cancel-confirm/<token>"
)
def ticket_cancel_confirm(ticket_id, token):

    return cancel_ticket_confirm(
        ticket_id,
        token
    )


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


@app.route("/test-r2")
def test_r2():

    try:

        response = r2.get_object(
            Bucket=R2_BUCKET,
            Key="サンプルPDF.pdf"
        )

        return response["Body"].read(), 200, {
            "Content-Type": "application/pdf",
            "Content-Disposition": "attachment; filename=sample.pdf"
        }

    except Exception as e:

        print(
            "R2取得エラー:",
            repr(e)
        )

        return "R2取得失敗", 500


@app.route("/")
def home():

    return "Webhook server is running"


@app.route("/admin/export")
@admin_required
def admin_export():
    return export_excel()


@app.route("/admin")
@admin_required
def admin():

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    # =========================
    # ticketsテーブルの存在確認
    # =========================

    cur.execute("""
        SELECT to_regclass('public.tickets')
    """)

    tickets_exists = cur.fetchone()[0] is not None

    ticket_rows = []

    if tickets_exists:

        cur.execute("""

            ALTER TABLE tickets

            ADD COLUMN IF NOT EXISTS email VARCHAR(320)

            """)

        cur.execute("""
            SELECT
                created_at,
                ticket_type,
                purchaser_name,
                email,
                reservation_name,
                used,
                used_at,
                1,
                amount
            FROM tickets
            ORDER BY created_at DESC
        """)

        ticket_rows = cur.fetchall()

    # =========================
    # goodsテーブルの存在確認
    # =========================

    cur.execute("""
        SELECT to_regclass('public.goods')
    """)

    goods_exists = cur.fetchone()[0] is not None

    goods_rows = []

    if goods_exists:

        cur.execute("""
            SELECT
                purchased_at,
                goods_type,
                product_name,
                purchaser_name,
                email,
                quantity,
                amount
            FROM goods
            ORDER BY purchased_at DESC
        """)

        goods_rows = cur.fetchall()

    # =========================
    # 売上集計
    # =========================

    ticket_count = len(ticket_rows)

    ticket_sales = sum(
        row[8] or 0
        for row in ticket_rows
    )

    goods_count = sum(
        row[5] or 0
        for row in goods_rows
    )

    goods_sales = sum(
        row[6] or 0
        for row in goods_rows
    )

    total_sales = (
        ticket_sales
        + goods_sales
    )

    # =========================
    # HTML
    # =========================

    html = """

    <!DOCTYPE html>

    <html lang="ja">

    <head>

        <meta charset="UTF-8">

        <title>マイマケ 管理画面</title>

        <style>

            body {
                font-family: Arial, sans-serif;
                margin: 30px;
                background: #f5f5f5;
            }

            h1 {
                margin-bottom: 30px;
            }

            .summary {
                display: flex;
                gap: 20px;
                margin-bottom: 40px;
                flex-wrap: wrap;
            }

            .box {
                background: white;
                border: 1px solid #ccc;
                padding: 20px;
                min-width: 150px;
            }

            .number {
                font-size: 24px;
                font-weight: bold;
                margin-top: 10px;
            }

            table {
                border-collapse: collapse;
                width: 100%;
                background: white;
            }

            th,
            td {
                border: 1px solid #ccc;
                padding: 10px;
                text-align: left;
            }

            th {
                background: #f2f2f2;
            }

            .empty {
                background: white;
                padding: 30px;
                text-align: center;
                color: #666;
            }

        </style>

    </head>

    <body>

        <h1>マイマケ 管理画面</h1>


        <h2>売上概要</h2>

        <div class="summary">

            <div class="box">

                チケット販売

                <div class="number">
                    {{ ticket_count }}枚
                </div>

            </div>


            <div class="box">

                物販販売

                <div class="number">
                    {{ goods_count }}個
                </div>

            </div>


            <div class="box">

                売上合計

                <div class="number">
                    {{ "{:,}".format(total_sales) }}円
                </div>

            </div>

        </div>

        <a href="/admin/export">
            <button type="button">
                Excelをダウンロード
            </button>
        </a>


        <h2>購入履歴</h2>

        {% if ticket_rows or goods_rows %}

        <table>

            <tr>

                <th>日時</th>
                <th>種類</th>
                <th>商品</th>
                <th>購入者</th>
                <th>メールアドレス</th>
                <th>お取り置き名</th>
                <th>状態</th>
                <th>無効になった日時</th>
                <th>数量</th>
                <th>金額</th>

            </tr>


            {% for row in ticket_rows %}
            <tr>
                <td>{{ row[0] }}</td>
                <td>チケット</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] or "" }}</td>
                <td>{{ row[3] or "" }}</td>

                <td>{{ row[4] or "" }}</td>

                {% if row[5] %}
                <td>無効</td>
                {% else %}
                <td>有効</td>
                {% endif %}

                <td>
                    {% if row[6] %}
                        {{ row[6] }}
                    {% else %}
                        -
                    {% endif %}
                </td>

                <td>1</td>
                <td>{{ "{:,}".format(row[8]) }}円</td>
            </tr>
            {% endfor %}


            {% for row in goods_rows %}

            <tr>

                <td>{{ row[0] }}</td>

                <td>{{ row[1] }}</td>

                <td>{{ row[2] }}</td>

                <td>{{ row[3] or "" }}</td>

                <td>{{ row[4] or "" }}</td>

                <td>-</td>  <!-- お取り置き名 -->

                <td>-</td>  <!-- 状態 -->

                <td>-</td>　<!-- 無効になった日時 -->

                <td>{{ row[5] }}</td>

                <td>{{ "{:,}".format(row[6]) }}円</td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <div class="empty">
            まだ購入履歴はありません。
        </div>

        {% endif %}

    </body>

    </html>

    """

    cur.close()
    conn.close()

    return render_template_string(
        html,
        ticket_rows=ticket_rows,
        goods_rows=goods_rows,
        ticket_count=ticket_count,
        goods_count=goods_count,
        total_sales=total_sales
    )

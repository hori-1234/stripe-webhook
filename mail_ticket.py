import os
import base64
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

def send_ticket_email(session, issued_tickets, stripe_fee):

    try:

        customer_details = session.get("customer_details") or {}

        email = customer_details.get("email")
        purchaser_name = customer_details.get("name")

        if not email:
            print("購入者のメールアドレスがありません")
            return

        print(
            "チケットメール送信先:",
            email
        )

        text = f"""
{purchaser_name} 様

チケットをご購入いただきありがとうございます。

以下のチケットを発行しました。

"""

        for ticket in issued_tickets:

            text += f"""
チケット種類: {ticket["ticket_type"]}
発行番号: {ticket["issue_number"]}
チケットID: {ticket["ticket_id"]}
商品価格: {ticket["amount"] - stripe_fee:,}円
手数料: {stripe_fee:,}円
支払合計金額: {ticket["amount"]:,}円

"""

        text += """
チケットIDは入場時に使用します。

よろしくお願いいたします。
"""

        attachments = []

        for ticket in issued_tickets:

            qr_base64 = base64.b64encode(
                ticket["qr_bytes"]
            ).decode("utf-8")

            attachments.append({
                "filename": f'{ticket["ticket_id"]}.png',
                "content": qr_base64
            })

        print(
            "QR画像の添付準備完了"
        )

        print(
            "添付ファイル数:",
            len(attachments)
        )

        print(
            "Resendへメール送信要求を送信します"
        )

        response = resend.Emails.send({
            "from": "shop@nwoshi.com",
            "to": [email],
            "subject": "マイマケ｜チケットのご購入ありがとうございます",
            "text": text,
            "attachments": attachments
        })

        print(
            "Resendからの応答:",
            response
        )

        print(
            "チケットメール送信成功"
        )

    except Exception as e:

        print(
            "メール送信中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        raise

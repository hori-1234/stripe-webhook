import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]


def send_goods_email(session, goods_items):

    try:

        customer_details = session.get("customer_details") or {}

        email = customer_details.get("email")
        purchaser_name = customer_details.get("name")

        if not email:
            print("購入者のメールアドレスがありません")
            return

        print(
            "物販購入確認メール送信先:",
            email
        )

        text = f"""
{purchaser_name} 様

物販をご購入いただきありがとうございます。

以下の商品をご購入いただきました。

"""

        for item in goods_items:

            product = item.price.product

            product_name = product.name
            quantity = item.quantity
            amount = item.amount_total

            text += f"""
商品名: {product_name}
数量: {quantity}
購入金額: {amount}円

"""

        text += """
ご購入内容をご確認ください。

よろしくお願いいたします。
"""

        print(
            "Resendへメール送信要求を送信します"
        )

        response = resend.Emails.send({
            "from": "shop@nwoshi.com",
            "to": [email],
            "subject": "マイマケ｜商品のご購入ありがとうございます",
            "text": text
        })

        print(
            "Resendからの応答:",
            response
        )

        print(
            "物販購入確認メール送信成功"
        )

    except Exception as e:

        print(
            "物販購入確認メール送信中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        raise

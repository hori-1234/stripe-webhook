import os
import base64
import boto3
import resend


resend.api_key = os.environ["RESEND_API_KEY"]


r2 = boto3.client(
    "s3",
    endpoint_url=os.environ["R2_ENDPOINT"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"]
)

R2_BUCKET = os.environ["R2_BUCKET_NAME"]


def save_digital_goods(cur, line_items, session):

    for item in line_items.data:

        product = item.price.product

        product_name = product.name

        metadata = product.metadata.to_dict()

        goods_type = metadata.get("goods_type")

        pdf_key = metadata.get("pdf_key")

        quantity = item.quantity

        amount = item.amount_total

        customer_details = session.get("customer_details") or {}

        purchaser_name = customer_details.get("name")
        email = customer_details.get("email")

        payment_intent_id = session.get("payment_intent")

        print("デジタル商品処理")
        print("物販種類:", goods_type)
        print("商品名:", product_name)
        print("PDFキー:", pdf_key)
        print("購入者名:", purchaser_name)
        print("メールアドレス:", email)
        print("購入数量:", quantity)
        print("購入金額:", amount)
        print("Stripe決済ID:", payment_intent_id)

        if not pdf_key:

            print(
                "PDFキーが設定されていません"
            )

            continue

        if not email:

            print(
                "購入者のメールアドレスがありません"
            )

            continue

        try:

            print(
                "R2からPDFを取得します"
            )

            response = r2.get_object(
                Bucket=R2_BUCKET,
                Key=pdf_key
            )

            pdf_bytes = response["Body"].read()

            print(
                "R2からPDFを取得しました"
            )

            print(
                "PDFデータサイズ:",
                len(pdf_bytes),
                "bytes"
            )

            pdf_base64 = base64.b64encode(
                pdf_bytes
            ).decode("utf-8")

            attachments = [
                {
                    "filename": pdf_key,
                    "content": pdf_base64
                }
            ]

            print(
                "PDF添付の準備完了"
            )

            text = f"""
{purchaser_name} 様

PDF商品をご購入いただきありがとうございます。

以下の商品を添付いたしました。

商品名: {product_name}
数量: {quantity}
購入金額: {amount}円

添付PDFをご確認ください。

よろしくお願いいたします。
"""

            print(
                "PDF購入メール送信先:",
                email
            )

            print(
                "ResendへPDF添付メール送信要求を送信します"
            )

            resend_response = resend.Emails.send({
                "from": "shop@nwoshi.com",
                "to": [email],
                "subject": "マイマケ｜PDF商品のご購入ありがとうございます",
                "text": text,
                "attachments": attachments
            })

            print(
                "Resendからの応答:",
                resend_response
            )

            print(
                "PDF購入メール送信成功"
            )

        except Exception as e:

            print(
                "PDF商品の処理中にエラーが発生しました"
            )

            print(
                "エラー内容:",
                repr(e)
            )

            raise

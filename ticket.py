import secrets
import qrcode
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def issue_tickets(cur, line_items, session):
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

    # メールアドレス列を追加
    cur.execute("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS email VARCHAR(320)
    """)


    # お取り置き名列を追加
    cur.execute("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS reservation_name VARCHAR(200)
    """)

    cur.execute("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS payment_intent_id VARCHAR(255)
    """)

    # Stripeのお取り置き名を取得
    custom_fields = session.get("custom_fields") or []

    reservation_name = None

    for field in custom_fields:
        label = field.get("label") or {}

        if label.get("custom") == "お取り置き(出演者名)":
            text_data = field.get("text") or {}
            reservation_name = text_data.get("value")
            break

    print("お取り置き名:", reservation_name)


    # チケットごとの連番管理テーブル
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ticket_counters (
            ticket_type VARCHAR(100) PRIMARY KEY,
            next_number INTEGER NOT NULL
        )
    """)

    issued_tickets = []

    for item in line_items.data:

        price_id = item.price.id
        quantity = item.quantity

        print("購入されたPrice ID:", price_id)
        print("購入数量:", quantity)

        product = item.price.product

        product_image_url = None

        if product.images:
            product_image_url = product.images[0]

        print("商品画像URL:", product_image_url)

        metadata = product.metadata.to_dict()
        
        ticket_type = metadata.get("ticket_type")

        if not ticket_type:
            print(
                "ticket_typeが設定されていない商品です:",
                product.id
            )
            continue

        print("チケット種類:", ticket_type)

        for i in range(quantity):

            cur.execute("""
                INSERT INTO ticket_counters (
                    ticket_type,
                    next_number
                )
                VALUES (%s, 2)

                ON CONFLICT (ticket_type)
                DO UPDATE SET
                    next_number =
                    ticket_counters.next_number + 1

                RETURNING next_number
            """, (ticket_type,))

            next_number = cur.fetchone()[0]
            issue_number = next_number - 1

            ticket_id = "TKT-" + secrets.token_hex(8).upper()

            print("発行番号:", issue_number)
            print("チケットID:", ticket_id)

            # チケット確認ページのURL
            ticket_url = (
                "https://stripe-webhook-t3xu.onrender.com/ticket/"
                + ticket_id
            )


            # Stripeの商品画像を取得
            product_image = None

            if product_image_url:
                try:
                    response = requests.get(
                        product_image_url,
                        timeout=10
                    )
                    response.raise_for_status()

                    product_image = Image.open(
                        BytesIO(response.content)
                    ).convert("RGB")

                except Exception as e:
                    print("商品画像取得エラー:", e)

            # QRコードには確認URLを入れる
            qr = qrcode.make(ticket_url).convert("RGB")


            if product_image:
                product_image.thumbnail(
                    (200, 200)
                )

            # QRコード上部に表示する文字
            title_text = ticket_type
            number_text = f"発行番号：{issue_number}"
            reservation_text = f"お取り置き：{reservation_name or '-'}"

            # フォント
            font_path = "NotoSansJP-Regular.ttf"

            title_font_size = 40
            title_font = ImageFont.truetype(font_path, title_font_size)

            while True:
                title_bbox = title_font.getbbox(title_text)
                title_width = title_bbox[2] - title_bbox[0]

                if title_width <= 330 or title_font_size <= 20:
                    break

                title_font_size -= 2
                title_font = ImageFont.truetype(
                    font_path,
                    title_font_size
                )
            
            number_font = ImageFont.truetype(font_path, 36)
            reservation_font = ImageFont.truetype(font_path, 30)

            # 文字部分の高さ
            header_height = 360

            # QRコードのサイズ
            qr_width, qr_height = qr.size

            # 上部に文字領域を追加
            ticket_image = Image.new(
                "RGB",
                (qr_width, qr_height + header_height),
                "white"
            )

            # QRコードを下に配置
            ticket_image.paste(qr, (0, header_height))

            # 商品画像を上部中央に配置
            if product_image:
                image_width, image_height = product_image.size

                image_x = (qr_width - image_width) // 2

                ticket_image.paste(
                    product_image,
                    (image_x, 10)
                )

            draw = ImageDraw.Draw(ticket_image)

            # チケット名
            title_bbox = draw.textbbox(
                (0, 0),
                title_text,
                font=title_font
            )

            title_width = title_bbox[2] - title_bbox[0]

            draw.text(
                ((qr_width - title_width) // 2, 240),
                title_text,
                fill="black",
                font=title_font
            )

            # 発行番号
            number_bbox = draw.textbbox(
                (0, 0),
                number_text,
                font=number_font
            )

            number_width = number_bbox[2] - number_bbox[0]

            draw.text(
                ((qr_width - number_width) // 2, 280),
                number_text,
                fill="black",
                font=number_font
            )

            # お取り置き名
            reservation_bbox = draw.textbbox(
                (0, 0),
                reservation_text,
                font=reservation_font
            )

            reservation_width = reservation_bbox[2] - reservation_bbox[0]

            draw.text(
                ((qr_width - reservation_width) // 2, 330),
                reservation_text,
                fill="black",
                font=reservation_font
            )

            # PNG化
            qr_buffer = BytesIO()
            ticket_image.save(qr_buffer, format="PNG")
            qr_bytes = qr_buffer.getvalue()


            print("QRコードを生成しました")
            print("QRデータサイズ:", len(qr_bytes), "bytes")
            print("QR確認URL:", ticket_url)

            customer_details = session.get(
                "customer_details"
            ) or {}

            purchaser_name = customer_details.get("name")
            email = customer_details.get("email")

            amount = item.amount_total // quantity
            
            cur.execute("""
                INSERT INTO tickets (
                    ticket_type,
                    issue_number,
                    ticket_id,
                    purchaser_name,
                    email,
                    reservation_name,
                    amount,
                    payment_intent_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                email,
                reservation_name,
                amount,
                session.get("payment_intent")
            ))
            
            issued_tickets.append({
                "ticket_type": ticket_type,
                "issue_number": issue_number,
                "ticket_id": ticket_id,
                "purchaser_name": purchaser_name,
                "email": email,
                "reservation_name": reservation_name,
                "amount": amount,
                "qr_bytes": qr_bytes
            })

    print("チケットをDBに保存しました")

    return issued_tickets

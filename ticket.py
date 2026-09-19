import secrets
import qrcode
from io import BytesIO


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

            # QRコードには確認URLを入れる
            qr = qrcode.make(ticket_url)

            qr_buffer = BytesIO()
            qr.save(qr_buffer, format="PNG")
            qr_bytes = qr_buffer.getvalue()

            print("QRコードを生成しました")
            print("QRデータサイズ:", len(qr_bytes), "bytes")
            print("QR確認URL:", ticket_url)

            purchaser_name = session.get(
                "customer_details",
                {}
            ).get("name")

            amount = item.amount_total // quantity

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
                purchaser_name,
                amount
            ))

            issued_tickets.append({
                "ticket_type": ticket_type,
                "issue_number": issue_number,
                "ticket_id": ticket_id,
                "purchaser_name": purchaser_name,
                "amount": amount,
                "qr_bytes": qr_bytes
            })

    print("チケットをDBに保存しました")

    return issued_tickets

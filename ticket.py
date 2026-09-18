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

    # 発行したチケット情報を保存するリスト
    issued_tickets = []

    # 商品ごとに処理
    for item in line_items.data:

        price_id = item.price.id
        quantity = item.quantity

        print("購入されたPrice ID:", price_id)
        print("購入数量:", quantity)

        # Stripeの商品を取得
        product = item.price.product

        # 商品メタデータからチケット種類を取得
        metadata = product.metadata.to_dict()
        ticket_type = metadata.get("ticket_type")

        # ticket_typeが設定されていない商品
        if not ticket_type:
            print("ticket_typeが設定されていない商品です:", product.id)
            continue

        print("チケット種類:", ticket_type)

        # 数量分のチケットを発行
        for i in range(quantity):

            # チケット種類ごとの連番を取得
            cur.execute("""
                INSERT INTO ticket_counters (ticket_type, next_number)
                VALUES (%s, 2)
                ON CONFLICT (ticket_type)
                DO UPDATE SET next_number = ticket_counters.next_number + 1
                RETURNING next_number
            """, (ticket_type,))

            next_number = cur.fetchone()[0]

            issue_number = next_number - 1

            # チケットIDを生成
            ticket_id = "TKT-" + secrets.token_hex(8).upper()

            print("発行番号:", issue_number)
            print("チケットID:", ticket_id)

            # QRコードを生成
            qr = qrcode.make(ticket_id)

            # QR画像をメモリ上に作成
            qr_buffer = BytesIO()
            qr.save(qr_buffer, format="PNG")

            # 画像データを取得
            qr_bytes = qr_buffer.getvalue()

            print("QRコードを生成しました")
            print("QRデータサイズ:", len(qr_bytes), "bytes")

            # 購入者名
            purchaser_name = session.get("customer_details", {}).get("name")

            # チケット情報をDBへ保存
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
                item.amount_total // quantity
            ))

            # 発行したチケット情報を保存
            issued_tickets.append({
                "ticket_type": ticket_type,
                "issue_number": issue_number,
                "ticket_id": ticket_id,
                "purchaser_name": purchaser_name,
                "amount": item.amount_total // quantity,
                "qr_bytes": qr_bytes
            })

    print("チケットをDBに保存しました")

    # 発行したチケット情報を返す
    return issued_tickets

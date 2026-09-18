def save_goods(cur, line_items, session):
    # goodsテーブルを作成
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goods (
            id SERIAL PRIMARY KEY,
            product_name VARCHAR(200) NOT NULL,
            purchaser_name VARCHAR(200),
            email VARCHAR(320),
            quantity INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_intent_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 商品ごとに処理
    for item in line_items.data:

        product = item.price.product

        # 商品名
        product_name = product.name

        # 購入数量
        quantity = item.quantity

        # 購入金額
        amount = item.amount_total

        # 購入者情報
        customer_details = session.get("customer_details") or {}

        purchaser_name = customer_details.get("name")
        email = customer_details.get("email")

        # Stripeの決済ID
        payment_intent_id = session.get("payment_intent")

        print("商品名:", product_name)
        print("購入者名:", purchaser_name)
        print("メールアドレス:", email)
        print("購入数量:", quantity)
        print("購入金額:", amount)
        print("Stripe決済ID:", payment_intent_id)

        # DBへ保存
        cur.execute("""
            INSERT INTO goods (
                product_name,
                purchaser_name,
                email,
                quantity,
                amount,
                payment_intent_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            product_name,
            purchaser_name,
            email,
            quantity,
            amount,
            payment_intent_id
        ))

    print("物販情報をDBに保存しました")

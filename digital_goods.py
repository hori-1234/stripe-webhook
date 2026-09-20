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

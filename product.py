from types import SimpleNamespace

from ticket import issue_tickets
from goods import save_goods
from digital_goods import save_digital_goods


def process_products(cur, line_items, session, stripe_fee):

    # チケット商品
    ticket_items = []

    # 現物物販
    goods_items = []

    # PDF物販
    digital_goods_items = []

    # Stripeの商品を分類
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

        # チケット
        if product_type == "ticket":

            ticket_items.append(item)

        # 物販
        elif product_type == "goods":

            if goods_type == "物販　PDF":

                digital_goods_items.append(item)

            else:

                goods_items.append(item)

        # product_typeがない商品
        else:

            print(
                "product_typeが設定されていない商品です:",
                product.id
            )

    # 発行されたチケット
    issued_tickets = []

    # チケット処理
    if ticket_items:

        print(
            "チケット処理を開始します"
        )

        ticket_line_items = SimpleNamespace(
            data=ticket_items
        )

        issued_tickets = issue_tickets(
            cur,
            ticket_line_items,
            session
        )

        print(
            "発行されたチケット数:",
            len(issued_tickets)
        )

        for ticket in issued_tickets:

            print(
                "発行チケット:",
                ticket["ticket_type"],
                ticket["issue_number"],
                ticket["ticket_id"]
            )

    # 現物物販処理
    if goods_items:

        print(
            "現物物販処理を開始します"
        )

        goods_line_items = SimpleNamespace(
            data=goods_items
        )

        save_goods(
            cur,
            goods_line_items,
            session
        )

    # PDF物販処理
    if digital_goods_items:

        print(
            "PDF物販処理を開始します"
        )

        digital_goods_line_items = SimpleNamespace(
            data=digital_goods_items
        )

        save_digital_goods(
            cur,
            digital_goods_line_items,
            session,
            stripe_fee
        )

    # 発行したチケットを返す
    return issued_tickets

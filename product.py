from types import SimpleNamespace

from ticket import issue_tickets
from goods import save_goods


def process_products(cur, line_items, session):

    # チケット商品
    ticket_items = []

    # 物販商品
    goods_items = []

    # Stripeの商品を分類
    for item in line_items.data:

        product = item.price.product

        metadata = product.metadata.to_dict()

        product_type = metadata.get("product_type")

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

    # 物販処理
    if goods_items:

        print(
            "物販処理を開始します"
        )

        goods_line_items = SimpleNamespace(
            data=goods_items
        )

        save_goods(
            cur,
            goods_line_items,
            session
        )

    # 発行したチケットを返す
    return issued_tickets

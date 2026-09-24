import os
from io import BytesIO
from datetime import datetime

import psycopg2
from flask import send_file
from openpyxl import Workbook

def excel_datetime(value):

    if isinstance(value, datetime):
        return value.replace(tzinfo=None)

    return value

def export_excel():

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    # 既存ticketsテーブルにemailカラムがなければ追加
    cur.execute("""
        ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS email VARCHAR(320)
    """)

    
    # チケット取得
    cur.execute("""
        SELECT
            tickets.created_at,
            ticket_type,
            purchaser_name,
            email,
            reservation_name,
            used,
            used_at,
            1,
            tickets.amount,
            tickets.payment_intent_id,
            payments.stripe_fee,
            payments.stripe_net
        FROM tickets
        LEFT JOIN payments
            ON tickets.payment_intent_id = payments.payment_intent_id
        ORDER BY tickets.created_at DESC
    """)

    ticket_rows = cur.fetchall()

    # 物販取得
    cur.execute("""
        SELECT
            goods.purchased_at,
            goods_type,
            product_name,
            purchaser_name,
            email,
            quantity,
            goods.amount,
            goods.payment_intent_id,
            payments.stripe_fee,
            payments.stripe_net
        FROM goods
        LEFT JOIN payments
            ON goods.payment_intent_id = payments.payment_intent_id
        ORDER BY goods.purchased_at DESC
    """)

    goods_rows = cur.fetchall()

    cur.close()
    conn.close()

    # Excel作成
    wb = Workbook()
    ws = wb.active
    ws.title = "購入履歴"

    # 見出し
    ws.append([
        "日時",
        "種類",
        "商品",
        "購入者",
        "メールアドレス",
        "お取り置き名",
        "状態",
        "無効になった日時",
        "数量",
        "売上金額",
        "合計金額",
        "手数料",
        "販売利益",
        "決済ID"
    ])

    shown_payment_ids = set()

    # チケット
    for row in ticket_rows:

        if row[5]:
            status = "無効"
        else:
            status = "有効"

        if row[9] and row[9] not in shown_payment_ids:
            total_amount = (
                row[10] + row[11]
                if row[10] is not None and row[11] is not None
                else None
            )
            stripe_fee = row[10]
            stripe_net = row[11]

            shown_payment_ids.add(row[9])

        else:
            total_amount = None
            stripe_fee = None
            stripe_net = None
        
        ws.append([
            excel_datetime(row[0]),
            "チケット",
            row[1],
            row[2],
            row[3],
            row[4],
            status,
            excel_datetime(row[6]),
            1,
            row[8],       # 売上金額
            total_amount, # 合計金額
            stripe_fee,   # 手数料
            stripe_net,   # 販売利益
            row[9]        # 決済ID
        ])

    # 物販
    for row in goods_rows:

        if row[7] and row[7] not in shown_payment_ids:
            total_amount = (
                row[8] + row[9]
                if row[8] is not None and row[9] is not None
                else None
            )
            stripe_fee = row[8]
            stripe_net = row[9]

            shown_payment_ids.add(row[7])

        else:
            total_amount = None
            stripe_fee = None
            stripe_net = None

        ws.append([
            excel_datetime(row[0]),
            row[1],
            row[2],
            row[3],
            row[4],
            "-",  # お取り置き名
            "-",  # 状態
            "-",  # 無効になった日時
            row[5],       # 数量
            row[6],       # 売上金額
            total_amount, # 合計金額
            stripe_fee,   # 手数料
            stripe_net,   # 販売利益
            row[7]        # 決済ID
        ])
         
    # メモリ上にExcelを保存
    output = BytesIO()

    wb.save(output)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="maimake_sales.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

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
            created_at,
            ticket_type,
            purchaser_name,
            email,
            reservation_name,
            used,
            used_at,
            1,
            amount
        FROM tickets
        ORDER BY created_at DESC
    """)

    ticket_rows = cur.fetchall()

    # 物販取得
    cur.execute("""
        SELECT
            purchased_at,
            goods_type,
            product_name,
            purchaser_name,
            email,
            quantity,
            amount
        FROM goods
        ORDER BY purchased_at DESC
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
        "金額"
    ])

    # チケット
    for row in ticket_rows:

        if row[5]:
            status = "無効"
        else:
            status = "有効"

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
            row[8]
        ])

    # 物販
    for row in goods_rows:

        ws.append([
            excel_datetime(row[0]),
            row[1],
            row[2],
            row[3],
            row[4],
            "-",  # お取り置き名
            "-",  # 状態
            "-",  # 無効になった日時
            row[5],
            row[6]
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

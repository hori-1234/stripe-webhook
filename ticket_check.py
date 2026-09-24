import psycopg2
import os
import secrets
import resend
from datetime import timezone, timedelta


JST = timezone(timedelta(hours=9))


def format_used_at(used_at):

    if used_at is None:
        return None

    if used_at.tzinfo is None:
        used_at = used_at.replace(tzinfo=timezone.utc)

    used_at = used_at.astimezone(JST)

    return used_at.strftime("%Y年%-m月%-d日 %H:%M")


def check_ticket(ticket_id):

    print(
        "チケット確認:",
        ticket_id
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS used
            BOOLEAN NOT NULL DEFAULT FALSE
        """)

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS used_at
            TIMESTAMP WITH TIME ZONE
        """)

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS cancel_token
            VARCHAR(255)
        """)

        conn.commit()

        cur.execute("""
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount,
                used,
                used_at,
                reservation_name
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))

        row = cur.fetchone()

        if row is None:

            print(
                "チケットが見つかりません:",
                ticket_id
            )

            return """
            <!DOCTYPE html>
            <html lang="ja">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1.0">
                <title>チケット確認</title>
            </head>

            <body style="
                font-family: sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            ">

                <div style="
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px 20px;
                    border-radius: 15px;
                    box-sizing: border-box;
                    text-align: center;
                ">

                    <h1 style="font-size: 32px;">
                        チケット無効
                    </h1>

                    <p style="font-size: 20px;">
                        このチケットは存在しません。
                    </p>

                </div>

            </body>
            </html>
            """, 404

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]
        used_at = row[6]
        reservation_name = row[7]
        print("確認画面のお取り置き名:", reservation_name)

        print(
            "チケットが見つかりました"
        )

        print(
            "チケット種類:",
            ticket_type
        )

        print(
            "発行番号:",
            issue_number
        )

        print(
            "チケットID:",
            ticket_id
        )

        print(
            "購入者:",
            purchaser_name
        )

        print(
            "金額:",
            amount
        )

        print(
            "使用済み:",
            used
        )

        print(
            "使用日時:",
            used_at
        )

        if used:

            used_at_text = format_used_at(used_at)

            if used_at_text:

                used_at_html = f"""
                <p>
                    <strong>使用日時</strong><br>
                    {used_at_text}
                </p>
                """

            else:

                used_at_html = ""

            return f"""
            <!DOCTYPE html>
            <html lang="ja">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1.0">
                <title>チケット確認</title>
            </head>

            <body style="
                font-family: sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            ">

                <div style="
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px 20px;
                    border-radius: 15px;
                    box-sizing: border-box;
                ">

                    <h1 style="
                        font-size: 34px;
                        text-align: center;
                        margin-bottom: 25px;
                    ">
                        使用済み
                    </h1>

                    <p style="
                        font-size: 21px;
                        text-align: center;
                        margin-bottom: 30px;
                    ">
                        このチケットはすでに使用されています。
                    </p>

                    <div style="
                        font-size: 20px;
                        line-height: 1.8;
                    ">

                        <p>
                            <strong>チケット種類</strong><br>
                            {ticket_type}
                        </p>

                        <p>
                            <strong>発行番号</strong><br>
                            {issue_number}
                        </p>

                        <p>
                            <strong>チケットID</strong><br>
                            {ticket_id}
                        </p>

                        <p>
                            <strong>購入者</strong><br>
                            {purchaser_name}
                        </p>

                        <p>
                            <strong>お取り置き名</strong><br>
                            {reservation_name or "-"}
                        </p>

                        <p>
                            <strong>料金</strong><br>
                            {amount:,}円
                        </p>

                        {used_at_html}

                        <form
                            method="GET"
                            action="/ticket/{ticket_id}/cancel"
                            style="margin-top: 35px;"
                        >

                            <button
                                type="submit"
                                style="
                                    width: 100%;
                                    padding: 18px;
                                    font-size: 23px;
                                    font-weight: bold;
                                    border: none;
                                    border-radius: 10px;
                                    cursor: pointer;
                                "
                            >
                                使用取消
                            </button>

                        </form>

                    </div>

                </div>

            </body>
            </html>
            """, 400

        return f"""
        <!DOCTYPE html>
        <html lang="ja">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>チケット確認</title>
        </head>

        <body style="
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        ">

            <div style="
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px 20px;
                border-radius: 15px;
                box-sizing: border-box;
            ">

                <h1 style="
                    font-size: 34px;
                    text-align: center;
                    margin-bottom: 20px;
                ">
                    チケット確認
                </h1>

                <div style="
                    text-align: center;
                    font-size: 30px;
                    font-weight: bold;
                    margin-bottom: 30px;
                ">
                    有効
                </div>

                <div style="
                    font-size: 21px;
                    line-height: 1.8;
                ">

                    <p>
                        <strong>チケット種類</strong><br>
                        {ticket_type}
                    </p>

                    <p>
                        <strong>発行番号</strong><br>
                        {issue_number}
                    </p>

                    <p>
                        <strong>チケットID</strong><br>
                        {ticket_id}
                    </p>

                    <p>
                        <strong>購入者</strong><br>
                        {purchaser_name}
                    </p>

                    <p>
                        <strong>料金</strong><br>
                        {amount:,}円
                    </p>

                </div>

                <form
                    method="POST"
                    action="/ticket/{ticket_id}/use"
                    style="margin-top: 35px;"
                >

                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 25px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
                        "
                    >
                        入場OK
                    </button>

                </form>


                <form
                    method="GET"
                    action="/ticket/{ticket_id}/cancel"
                    style="margin-top: 15px;"
                >
                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 25px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
                        "
                    >
                        キャンセル
                    </button>
                </form>
                
            </div>

        </body>
        </html>
        """

    except Exception as e:

        conn.rollback()

        print(
            "チケット確認中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "チケット確認中にエラーが発生しました",
            500
        )

    finally:

        cur.close()
        conn.close()


def confirm_use_ticket(ticket_id):

    print(
        "入場確認画面:",
        ticket_id
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount,
                used,
                used_at
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))

        row = cur.fetchone()

        if row is None:

            return (
                "チケットが見つかりません",
                404
            )

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]

        if used:

            return """
            <!DOCTYPE html>
            <html lang="ja">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1.0">
                <title>使用済み</title>
            </head>

            <body style="
                font-family: sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            ">

                <div style="
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px 20px;
                    border-radius: 15px;
                    box-sizing: border-box;
                    text-align: center;
                ">

                    <h1 style="font-size: 34px;">
                        使用済み
                    </h1>

                    <p style="font-size: 21px;">
                        このチケットはすでに使用されています。
                    </p>

                </div>

            </body>
            </html>
            """, 400

        return f"""
        <!DOCTYPE html>
        <html lang="ja">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>入場確認</title>
        </head>

        <body style="
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        ">

            <div style="
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px 20px;
                border-radius: 15px;
                box-sizing: border-box;
                text-align: center;
            ">

                <h1 style="
                    font-size: 34px;
                    margin-bottom: 25px;
                ">
                    入場確認
                </h1>

                <p style="
                    font-size: 22px;
                    font-weight: bold;
                ">
                    このチケットを使用済みにしますか？
                </p>

                <div style="
                    text-align: left;
                    font-size: 20px;
                    line-height: 1.8;
                    margin-top: 30px;
                ">

                    <p>
                        <strong>チケット種類</strong><br>
                        {ticket_type}
                    </p>

                    <p>
                        <strong>発行番号</strong><br>
                        {issue_number}
                    </p>

                    <p>
                        <strong>チケットID</strong><br>
                        {ticket_id}
                    </p>

                    <p>
                        <strong>購入者</strong><br>
                        {purchaser_name}
                    </p>

                    <p>
                        <strong>料金</strong><br>
                        {amount:,}円
                    </p>

                </div>

                <form
                    method="POST"
                    action="/ticket/{ticket_id}/confirm-use"
                    style="margin-top: 35px;"
                >

                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 25px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
                            margin-bottom: 15px;
                        "
                    >
                        OK
                    </button>

                </form>

                <form
                    method="GET"
                    action="/ticket/{ticket_id}"
                >

                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 25px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
                        "
                    >
                        NO
                    </button>

                </form>

            </div>

        </body>
        </html>
        """

    except Exception as e:

        conn.rollback()

        print(
            "入場確認画面でエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "入場確認画面でエラーが発生しました",
            500
        )

    finally:

        cur.close()
        conn.close()


def use_ticket(ticket_id):

    print(
        "チケット使用処理:",
        ticket_id
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS used
            BOOLEAN NOT NULL DEFAULT FALSE
        """)

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS used_at
            TIMESTAMP WITH TIME ZONE
        """)

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS cancel_token
            VARCHAR(255)
        """)

        conn.commit()

        cur.execute("""
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount,
                used,
                used_at
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))

        row = cur.fetchone()

        if row is None:

            conn.rollback()

            return """
            <!DOCTYPE html>
            <html lang="ja">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1.0">
                <title>チケット確認</title>
            </head>

            <body style="
                font-family: sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            ">

                <div style="
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px 20px;
                    border-radius: 15px;
                    box-sizing: border-box;
                    text-align: center;
                ">

                    <h1 style="font-size: 32px;">
                        チケット無効
                    </h1>

                    <p style="font-size: 20px;">
                        このチケットは存在しません。
                    </p>

                </div>

            </body>
            </html>
            """, 404

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]
        used_at = row[6]

        if used:

            conn.rollback()

            print(
                "このチケットは使用済みです:",
                ticket_id
            )

            used_at_text = format_used_at(used_at)

            if used_at_text:

                used_at_html = f"""
                <p>
                    <strong>使用日時</strong><br>
                    {used_at_text}
                </p>
                """

            else:

                used_at_html = ""

            return f"""
            <!DOCTYPE html>
            <html lang="ja">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1.0">
                <title>チケット確認</title>
            </head>

            <body style="
                font-family: sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            ">

                <div style="
                    max-width: 500px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px 20px;
                    border-radius: 15px;
                    box-sizing: border-box;
                ">

                    <h1 style="
                        font-size: 34px;
                        text-align: center;
                    ">
                        使用済み
                    </h1>

                    <p style="
                        font-size: 21px;
                        text-align: center;
                    ">
                        このチケットはすでに使用されています。
                    </p>

                    <div style="
                        font-size: 20px;
                        line-height: 1.8;
                    ">

                        <p>
                            <strong>チケット種類</strong><br>
                            {ticket_type}
                        </p>

                        <p>
                            <strong>発行番号</strong><br>
                            {issue_number}
                        </p>

                        <p>
                            <strong>チケットID</strong><br>
                            {ticket_id}
                        </p>

                        <p>
                            <strong>購入者</strong><br>
                            {purchaser_name}
                        </p>

                        <p>
                            <strong>料金</strong><br>
                            {amount:,}円
                        </p>

                        {used_at_html}

                    </div>

                </div>

            </body>
            </html>
            """, 400

        cur.execute("""
            UPDATE tickets
            SET
                used = TRUE,
                used_at = CURRENT_TIMESTAMP
            WHERE ticket_id = %s
        """, (ticket_id,))

        conn.commit()

        print(
            "チケットを使用済みにしました:",
            ticket_id
        )

        return f"""
        <!DOCTYPE html>
        <html lang="ja">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>入場OK</title>
        </head>

        <body style="
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        ">

            <div style="
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px 20px;
                border-radius: 15px;
                box-sizing: border-box;
            ">

                <h1 style="
                    font-size: 36px;
                    text-align: center;
                    margin-bottom: 25px;
                ">
                    入場OK
                </h1>

                <p style="
                    font-size: 21px;
                    text-align: center;
                    margin-bottom: 30px;
                ">
                    チケットを使用済みにしました。
                </p>

                <div style="
                    font-size: 20px;
                    line-height: 1.8;
                ">

                    <p>
                        <strong>チケット種類</strong><br>
                        {ticket_type}
                    </p>

                    <p>
                        <strong>発行番号</strong><br>
                        {issue_number}
                    </p>

                    <p>
                        <strong>チケットID</strong><br>
                        {ticket_id}
                    </p>

                    <p>
                        <strong>購入者</strong><br>
                        {purchaser_name}
                    </p>

                    <p>
                        <strong>料金</strong><br>
                        {amount:,}円
                    </p>

                    <p>
                        <strong>使用日時</strong><br>
                        入場処理済み
                    </p>

                </div>

            </div>

        </body>

        </html>
        """

    except Exception as e:

        conn.rollback()

        print(
            "チケット使用処理中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "チケット使用処理中にエラーが発生しました",
            500
        )

    finally:

        cur.close()
        conn.close()


def cancel_ticket_request(ticket_id):

    print(
        "使用取消画面:",
        ticket_id
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount,
                used
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))

        row = cur.fetchone()

        if row is None:

            return (
                "チケットが見つかりません",
                404
            )

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]

        if not used:

            return """
            <!DOCTYPE html>
            <html lang="ja">

            <head>
                <meta charset="UTF-8">
                <meta name="viewport"
                      content="width=device-width, initial-scale=1.0">
                <title>使用取消</title>
            </head>

            <body style="
                font-family: sans-serif;
                text-align: center;
                padding: 40px;
            ">

                <h1>使用取消</h1>

                <p style="font-size: 20px;">
                    このチケットは使用済みではありません。
                </p>

            </body>
            </html>
            """, 400

        return f"""
        <!DOCTYPE html>
        <html lang="ja">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>使用取消依頼</title>
        </head>

        <body style="
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        ">

            <div style="
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px 20px;
                border-radius: 15px;
                box-sizing: border-box;
                text-align: center;
            ">

                <h1 style="
                    font-size: 32px;
                    margin-bottom: 30px;
                ">
                    使用取消
                </h1>

                <p style="
                    font-size: 19px;
                    line-height: 1.8;
                    text-align: left;
                ">
                    ※誤って入場OKを押してしまった場合<br>
                    Xの運営アカウントまで連絡後、<br>
                    下記ボタンで処理を進めてください。
                </p>

                <div style="
                    text-align: left;
                    font-size: 20px;
                    line-height: 1.8;
                    margin-top: 30px;
                ">

                    <p>
                        <strong>チケット種類</strong><br>
                        {ticket_type}
                    </p>

                    <p>
                        <strong>発行番号</strong><br>
                        {issue_number}
                    </p>

                    <p>
                        <strong>チケットID</strong><br>
                        {ticket_id}
                    </p>

                    <p>
                        <strong>購入者</strong><br>
                        {purchaser_name}
                    </p>

                    <p>
                        <strong>料金</strong><br>
                        {amount:,}円
                    </p>

                </div>

                <form
                    method="POST"
                    action="/ticket/{ticket_id}/cancel-send"
                    style="margin-top: 35px;"
                >

                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 23px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
                        "
                    >
                        送信
                    </button>

                </form>

                <form
                    method="GET"
                    action="/ticket/{ticket_id}"
                    style="margin-top: 15px;"
                >

                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 23px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
                        "
                    >
                        キャンセル
                    </button>

                </form>

            </div>

        </body>
        </html>
        """

    except Exception as e:

        conn.rollback()

        print(
            "使用取消画面でエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "使用取消画面でエラーが発生しました",
            500
        )

    finally:

        cur.close()
        conn.close()


def cancel_ticket_send(ticket_id):

    print(
        "使用取消依頼送信:",
        ticket_id
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount,
                used
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))

        row = cur.fetchone()

        if row is None:

            return (
                "チケットが見つかりません",
                404
            )

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]

        if not used:

            return (
                "このチケットは使用済みではありません。",
                400
            )

        cur.execute("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS cancel_token
            VARCHAR(255)
        """)

        token = secrets.token_urlsafe(32)

        cur.execute("""
            UPDATE tickets
            SET cancel_token = %s
            WHERE ticket_id = %s
              AND used = TRUE
        """, (
            token,
            ticket_id
        ))

        conn.commit()

        cancel_url = (
            "https://stripe-webhook-t3xu.onrender.com"
            "/ticket/"
            + ticket_id
            + "/cancel-confirm/"
            + token
        )

        text = f"""
チケット使用キャンセル依頼

チケット種類: {ticket_type}
発行番号: {issue_number}
チケットID: {ticket_id}
購入者: {purchaser_name}
料金: {amount:,}円

下記URLを開くと、チケットの使用を取り消します。

{cancel_url}
"""

        print(
            "キャンセル依頼メール送信先:",
            "m27ac49764jfgvn@t.vodafone.ne.jp"
        )

        resend.Emails.send({
            "from": "shop@nwoshi.com",
            # ドメイン後修正
            "to": ["m27ac49764jfgvn@t.vodafone.ne.jp"],
            "subject": "チケット使用キャンセル依頼",
            "text": text
        })

        return """
        <!DOCTYPE html>
        <html lang="ja">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>使用取消依頼</title>
        </head>

        <body style="
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        ">

            <div style="
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px 20px;
                border-radius: 15px;
                box-sizing: border-box;
                text-align: center;
            ">

                <h1 style="
                    font-size: 32px;
                    margin-bottom: 30px;
                ">
                    送信完了
                </h1>

                <p style="
                    font-size: 21px;
                    line-height: 1.8;
                ">
                    使用取消依頼を運営へ送信しました。
                </p>

            </div>

        </body>
        </html>
        """

    except Exception as e:

        conn.rollback()

        print(
            "使用取消依頼送信中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "使用取消依頼の送信中にエラーが発生しました",
            500
        )

    finally:

        cur.close()
        conn.close()


def cancel_ticket_confirm(ticket_id, token):

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount,
                used,
                cancel_token
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))

        row = cur.fetchone()

        if row is None:

            return (
                "チケットが見つかりません",
                404
            )

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]
        cancel_token = row[6]

        if cancel_token != token:

            return (
                "この使用取消URLは無効です。",
                403
            )

        if not used:

            return (
                "このチケットはすでに使用取消されています。",
                400
            )

        cur.execute("""
            UPDATE tickets
            SET
                used = FALSE,
                used_at = NULL,
                cancel_token = NULL
            WHERE ticket_id = %s
              AND cancel_token = %s
              AND used = TRUE
        """, (
            ticket_id,
            token
        ))

        conn.commit()

        return f"""
        <!DOCTYPE html>
        <html lang="ja">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">
            <title>使用取消完了</title>
        </head>

        <body style="
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        ">

            <div style="
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px 20px;
                border-radius: 15px;
                box-sizing: border-box;
                text-align: center;
            ">

                <h1 style="
                    font-size: 32px;
                    margin-bottom: 30px;
                ">
                    使用取消完了
                </h1>

                <p style="
                    font-size: 21px;
                    line-height: 1.8;
                ">
                    チケットの使用を取り消しました。
                </p>

                <p style="
                    font-size: 20px;
                    line-height: 1.8;
                ">
                    発行番号: {issue_number}<br>
                    チケットID: {ticket_id}
                </p>

            </div>

        </body>
        </html>
        """

    except Exception as e:

        conn.rollback()

        print(
            "使用取消処理中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "使用取消処理中にエラーが発生しました",
            500
        )

    finally:

        cur.close()
        conn.close()

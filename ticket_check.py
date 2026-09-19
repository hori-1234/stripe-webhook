import psycopg2
import os
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

        # --------------------------------------------------
        # 使用済みの場合
        # --------------------------------------------------

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
                            <strong>料金</strong><br>
                            {amount:,}円
                        </p>

                        {used_at_html}

                    </div>

                </div>

            </body>
            </html>
            """, 400

        # --------------------------------------------------
        # 未使用の場合
        # --------------------------------------------------

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
        "チケット使用確認:",
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

        # --------------------------------------------------
        # すでに使用済みの場合
        # --------------------------------------------------

        if used:

            conn.rollback()

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

        # --------------------------------------------------
        # OK確認画面
        # --------------------------------------------------

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
            ">

                <h1 style="
                    font-size: 32px;
                    text-align: center;
                    margin-bottom: 30px;
                ">
                    入場確認
                </h1>

                <p style="
                    font-size: 22px;
                    text-align: center;
                    margin-bottom: 35px;
                ">
                    このチケットを使用済みにしますか？
                </p>

                <div style="
                    font-size: 20px;
                    line-height: 1.8;
                    margin-bottom: 35px;
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
                    style="margin-bottom: 15px;"
                >

                    <button
                        type="submit"
                        style="
                            width: 100%;
                            padding: 18px;
                            font-size: 26px;
                            font-weight: bold;
                            border: none;
                            border-radius: 10px;
                            cursor: pointer;
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
                            font-size: 26px;
                            font-weight: bold;
                            border: 2px solid #999;
                            border-radius: 10px;
                            background: white;
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
            "入場確認中にエラーが発生しました"
        )

        print(
            "エラー内容:",
            repr(e)
        )

        return (
            "入場確認中にエラーが発生しました",
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

        # --------------------------------------------------
        # すでに使用済みなら処理しない
        # --------------------------------------------------

        if used:

            conn.rollback()

            print(
                "このチケットはすでに使用済みです:",
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

        # --------------------------------------------------
        # 使用済みに変更
        # --------------------------------------------------

        cur.execute("""
            UPDATE tickets
            SET
                used = TRUE,
                used_at = CURRENT_TIMESTAMP
            WHERE ticket_id = %s
              AND used = FALSE
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

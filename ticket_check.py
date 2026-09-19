import psycopg2
import os


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
            SELECT
                ticket_type,
                issue_number,
                ticket_id,
                purchaser_name,
                amount
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
            <h1>チケット無効</h1>
            <p>このチケットは存在しません。</p>
            """, 404

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]

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

        return f"""
        <h1>チケット確認</h1>

        <p>チケット：有効</p>
        <p>チケット種類：{ticket_type}</p>
        <p>発行番号：{issue_number}</p>
        <p>チケットID：{ticket_id}</p>
        <p>購入者：{purchaser_name}</p>
        <p>金額：{amount}円</p>

        <form method="POST"
              action="/ticket/{ticket_id}/use">

            <button type="submit">
                入場OK
            </button>

        </form>
        """

    except Exception as e:

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

            conn.rollback()

            return """
            <h1>チケット無効</h1>
            <p>このチケットは存在しません。</p>
            """, 404

        ticket_type = row[0]
        issue_number = row[1]
        ticket_id = row[2]
        purchaser_name = row[3]
        amount = row[4]
        used = row[5]

        if used:

            conn.rollback()

            print(
                "このチケットは使用済みです:",
                ticket_id
            )

            return f"""
            <h1>使用済み</h1>

            <p>このチケットはすでに使用されています。</p>

            <p>チケット種類：{ticket_type}</p>
            <p>発行番号：{issue_number}</p>
            <p>チケットID：{ticket_id}</p>
            """, 400

        cur.execute("""
            UPDATE tickets
            SET used = TRUE
            WHERE ticket_id = %s
        """, (ticket_id,))

        conn.commit()

        print(
            "チケットを使用済みにしました:",
            ticket_id
        )

        return f"""
        <h1>入場OK</h1>

        <p>チケットを使用済みにしました。</p>

        <p>チケット種類：{ticket_type}</p>
        <p>発行番号：{issue_number}</p>
        <p>チケットID：{ticket_id}</p>
        <p>購入者：{purchaser_name}</p>
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

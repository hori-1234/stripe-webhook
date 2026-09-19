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

        # チケットIDをDBから検索
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

        # チケットが存在しない
        if row is None:

            print(
                "チケットが見つかりません:",
                ticket_id
            )

            return """
            <h1>チケット無効</h1>
            <p>このチケットは存在しません。</p>
            """, 404

        # DBから取得した情報
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

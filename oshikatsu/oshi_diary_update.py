import os
import psycopg2

from datetime import date


def update_oshi_diary(diary_id, user_id, form, conn=None):

    try:
        event_date = date.fromisoformat(
            form.get("event_date", "")
        )
    except ValueError:
        return False, "日付が正しくありません"

    event_name = form.get("event_name", "").strip()
    place = form.get("place", "").strip()
    performers = form.get("performers", "").strip()
    diary_text = form.get("diary_text", "").strip()

    if (
        len(event_name) > 500
        or len(place) > 500
        or len(performers) > 5000
        or len(diary_text) > 50000
    ):
        return False, "入力文字数が上限を超えています"

    own_connection = conn is None

    if own_connection:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE oshi_diaries
                SET
                    event_date = %s,
                    event_name = %s,
                    place = %s,
                    performers = %s,
                    diary_text = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND user_id = %s
                RETURNING id
            """, (
                event_date,
                event_name,
                place,
                performers,
                diary_text,
                diary_id,
                str(user_id)
            ))

            updated = cur.fetchone()

        if updated is None:
            if own_connection:
                conn.rollback()
            return False, "日記が見つかりません"

        if own_connection:
            conn.commit()

        return True, "更新しました"

    except Exception:
        if own_connection:
            conn.rollback()
        raise

    finally:
        if own_connection:
            conn.close()

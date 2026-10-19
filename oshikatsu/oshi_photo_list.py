import os
import psycopg2


def get_oshi_diary_photos(diary_id, user_id):

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    p.id,
                    p.photo_order
                FROM oshi_diary_photos AS p
                JOIN oshi_diaries AS d
                  ON d.id = p.diary_id
                WHERE p.diary_id = %s
                  AND d.user_id = %s
                ORDER BY p.photo_order, p.id
            """, (
                diary_id,
                str(user_id)
            ))

            photos = cur.fetchall()

    finally:
        conn.close()

    return photos

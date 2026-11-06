import os
import psycopg2


def init_artist_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS artist_submissions (
                        id BIGSERIAL PRIMARY KEY,
                        artist_name TEXT NOT NULL,
                        artist_type TEXT NOT NULL,
                        image_color TEXT,
                        image_key TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS artist_members (
                        id BIGSERIAL PRIMARY KEY,
                        submission_id BIGINT NOT NULL
                            REFERENCES artist_submissions(id)
                            ON DELETE CASCADE,
                        member_name TEXT NOT NULL,
                        member_color TEXT NOT NULL
                    )
                """)

    finally:
        conn.close()


def save_artist_submission(
    artist_name,
    artist_type,
    image_color,
    image_key,
    members
):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn:
            with conn.cursor() as cur:

                # 出演者情報を保存
                cur.execute("""
                    INSERT INTO artist_submissions (
                        artist_name,
                        artist_type,
                        image_color,
                        image_key
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    artist_name,
                    artist_type,
                    image_color,
                    image_key
                ))

                submission_id = cur.fetchone()[0]

                # グループの場合はメンバー情報も保存
                if artist_type == "group":
                    for member in members:
                        cur.execute("""
                            INSERT INTO artist_members (
                                submission_id,
                                member_name,
                                member_color
                            )
                            VALUES (%s, %s, %s)
                        """, (
                            submission_id,
                            member["name"],
                            member["color"]
                        ))

        return submission_id

    finally:
        conn.close()


def get_artist_submissions():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    artist_name,
                    artist_type,
                    image_color,
                    image_key,
                    created_at
                FROM artist_submissions
                ORDER BY created_at DESC, id DESC
            """)

            submissions = []

            for row in cur.fetchall():
                submission_id = row[0]

                submissions.append({
                    "id": submission_id,
                    "artist_name": row[1],
                    "artist_type": row[2],
                    "image_color": row[3],
                    "image_key": row[4],
                    "created_at": row[5].isoformat(),
                    "members": []
                })

            cur.execute("""
                SELECT
                    submission_id,
                    member_name,
                    member_color
                FROM artist_members
                ORDER BY id
            """)

            member_map = {}

            for submission_id, name, color in cur.fetchall():
                member_map.setdefault(submission_id, []).append({
                    "name": name,
                    "color": color
                })

            for submission in submissions:
                submission["members"] = member_map.get(
                    submission["id"], []
                )

            return submissions

    finally:
        conn.close()


def delete_artist_submission(submission_id, delete_image):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT image_key
                    FROM artist_submissions
                    WHERE id = %s
                    FOR UPDATE
                """, (submission_id,))

                row = cur.fetchone()

                if row is None:
                    return False

                image_key = row[0]

                # R2画像の削除に成功した場合のみDBを削除
                delete_image(image_key)

                cur.execute("""
                    DELETE FROM artist_submissions
                    WHERE id = %s
                """, (submission_id,))

        return True

    finally:
        conn.close()

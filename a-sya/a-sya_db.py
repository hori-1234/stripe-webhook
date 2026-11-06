
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


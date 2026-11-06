
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

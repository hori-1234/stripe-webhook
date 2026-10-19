import os
import psycopg2


def init_oshi_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS oshi_diaries (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        event_id BIGINT,
                        event_date DATE NOT NULL,
                        event_name TEXT NOT NULL DEFAULT '',
                        place TEXT NOT NULL DEFAULT '',
                        performers TEXT NOT NULL DEFAULT '',
                        diary_text TEXT NOT NULL DEFAULT '',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
    finally:
        conn.close()

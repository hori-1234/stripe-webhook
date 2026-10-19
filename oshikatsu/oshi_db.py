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

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS oshi_diary_photos (
                        id BIGSERIAL PRIMARY KEY,
                        diary_id BIGINT NOT NULL
                            REFERENCES oshi_diaries(id)
                            ON DELETE CASCADE,
                        r2_key TEXT NOT NULL,
                        photo_order INTEGER NOT NULL
                            CHECK (photo_order BETWEEN 1 AND 10),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (diary_id, photo_order)
                    )
                """)
                
    finally:
        conn.close()

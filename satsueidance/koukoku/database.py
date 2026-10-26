import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


def create_koukoku_tables():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS satsueidance_visitor_regions (
                visitor_id TEXT NOT NULL,
                visit_date DATE NOT NULL,
                prefecture TEXT NOT NULL,
                device_type TEXT NOT NULL,
                PRIMARY KEY (visit_date, visitor_id)
            )
        """)

        cur.execute("""
            ALTER TABLE satsueidance_usage_sessions
            ADD COLUMN IF NOT EXISTS prefecture TEXT
        """)

        cur.execute("""
            ALTER TABLE satsueidance_usage_sessions
            ADD COLUMN IF NOT EXISTS device_type TEXT
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

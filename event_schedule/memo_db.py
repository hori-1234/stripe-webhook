
import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


def create_schedule_memo_users_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_memo_users (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            ALTER TABLE schedule_memo_users
            ADD COLUMN IF NOT EXISTS google_sub TEXT
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_schedule_memo_users_google_sub
            ON schedule_memo_users (google_sub)
        """)

        cur.execute("""
            ALTER TABLE schedule_memo_users
            ADD COLUMN IF NOT EXISTS google_link_prompt_snoozed_until TIMESTAMPTZ
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def create_schedule_memo_login_codes_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_memo_login_codes (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            ALTER TABLE schedule_memo_login_codes
            ADD COLUMN IF NOT EXISTS request_ip TEXT
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_schedule_memo_login_codes_email
            ON schedule_memo_login_codes (email, created_at DESC)
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def create_schedule_memos_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_memos (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES schedule_memo_users(id)
                    ON DELETE CASCADE,

                event_id INTEGER,
                memo_date DATE NOT NULL,

                event_name TEXT,
                event_location TEXT,

                memo_text TEXT NOT NULL DEFAULT '',
                tag TEXT NOT NULL DEFAULT '付箋なし',
                tag_color TEXT NOT NULL DEFAULT '#FFF2B3',

                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT schedule_memos_target_check
                    CHECK (
                        event_id IS NOT NULL
                        OR event_name IS NULL
                    )
            )
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_schedule_memos_user_event
            ON schedule_memos (user_id, event_id)
            WHERE event_id IS NOT NULL
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_schedule_memos_user_date
            ON schedule_memos (user_id, memo_date)
            WHERE event_id IS NULL
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


def create_schedule_memo_alarms_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_memo_alarms (
                id BIGSERIAL PRIMARY KEY,

                memo_id BIGINT NOT NULL
                    REFERENCES schedule_memos(id)
                    ON DELETE CASCADE,

                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',

                scheduled_at TIMESTAMPTZ NOT NULL,

                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending',
                        'processing',
                        'sent',
                        'failed',
                        'cancelled'
                    )),

                sent_at TIMESTAMPTZ,
                attempt_count INTEGER NOT NULL DEFAULT 0,

                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_schedule_memo_alarms_pending
            ON schedule_memo_alarms (scheduled_at)
            WHERE status = 'pending'
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


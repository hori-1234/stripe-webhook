import os
import psycopg2


def get_syuwa_db_connection():
    return psycopg2.connect(
        os.environ["DATABASE_URL"]
    )


def init_syuwa_db():
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS syuwa_invites (
                    id BIGSERIAL PRIMARY KEY,
                    token_hash VARCHAR(64) NOT NULL UNIQUE,
                    status VARCHAR(20) NOT NULL DEFAULT 'unused',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    used_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ NOT NULL,
                    CONSTRAINT syuwa_invites_status_check
                        CHECK (status IN ('unused', 'applied', 'revoked'))
                )
            """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

import os
import psycopg2
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

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

def create_syuwa_invite():
    # 招待URLに使用するランダムなトークン
    token = secrets.token_urlsafe(32)

    # DBにはトークンそのものを保存しない
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    # 有効期限は発行から7日間
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO syuwa_invites (
                    token_hash,
                    expires_at
                )
                VALUES (%s, %s)
            """, (
                token_hash,
                expires_at
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    return token

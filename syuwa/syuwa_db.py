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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS syuwa_applications (
                    id BIGSERIAL PRIMARY KEY,
                    invite_id BIGINT NOT NULL UNIQUE
                        REFERENCES syuwa_invites(id),
                    applicant_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    comment TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMPTZ,
                    CONSTRAINT syuwa_applications_status_check
                        CHECK (status IN ('pending', 'approved', 'rejected'))
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


def verify_syuwa_invite(token):
    if not token:
        return False

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM syuwa_invites
                    WHERE token_hash = %s
                      AND status = 'unused'
                      AND expires_at > CURRENT_TIMESTAMP
                )
            """, (token_hash,))

            return cur.fetchone()[0]

    finally:
        conn.close()


def save_syuwa_application(token, applicant_name, email, comment):
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE syuwa_invites
                SET status = 'applied',
                    used_at = CURRENT_TIMESTAMP
                WHERE token_hash = %s
                  AND status = 'unused'
                  AND expires_at > CURRENT_TIMESTAMP
                RETURNING id
            """, (token_hash,))

            result = cur.fetchone()

            if result is None:
                conn.rollback()
                return False

            invite_id = result[0]

            cur.execute("""
                INSERT INTO syuwa_applications (
                    invite_id,
                    applicant_name,
                    email,
                    comment
                )
                VALUES (%s, %s, %s, %s)
            """, (
                invite_id,
                applicant_name,
                email,
                comment
            ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_syuwa_applications():
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    applicant_name,
                    email,
                    comment,
                    status,
                    created_at
                FROM syuwa_applications
                ORDER BY created_at DESC, id DESC
            """)

            return cur.fetchall()

    finally:
        conn.close()

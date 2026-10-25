import os
import psycopg2
import secrets
import hashlib
import re
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

            cur.execute("""
                ALTER TABLE syuwa_applications
                ADD COLUMN IF NOT EXISTS password_hash TEXT
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS syuwa_password_tokens (
                    id BIGSERIAL PRIMARY KEY,
                    application_id BIGINT NOT NULL
                        REFERENCES syuwa_applications(id),
                    token_hash VARCHAR(64) NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMPTZ NOT NULL,
                    used_at TIMESTAMPTZ
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


def update_syuwa_application_status(application_id, status):
    if status not in ("approved", "rejected"):
        return False

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE syuwa_applications
                SET status = %s,
                    approved_at = CASE
                        WHEN %s = 'approved'
                        THEN CURRENT_TIMESTAMP
                        ELSE NULL
                    END
                WHERE id = %s
                  AND status = 'pending'
                RETURNING id
            """, (
                status,
                status,
                application_id
            ))

            updated = cur.fetchone() is not None

        conn.commit()
        return updated

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def set_syuwa_password(application_id, password):
    from werkzeug.security import generate_password_hash

    password_hash = generate_password_hash(password)

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE syuwa_applications
                SET password_hash = %s
                WHERE id = %s
                  AND status = 'approved'
                  AND password_hash IS NULL
                RETURNING id
            """, (
                password_hash,
                application_id
            ))

            updated = cur.fetchone() is not None

        conn.commit()
        return updated

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def create_syuwa_password_token(application_id):
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM syuwa_applications
                WHERE id = %s
                  AND status = 'approved'
                  AND password_hash IS NULL
                FOR UPDATE
            """, (application_id,))

            if cur.fetchone() is None:
                conn.rollback()
                return None

            cur.execute("""
                UPDATE syuwa_password_tokens
                SET used_at = CURRENT_TIMESTAMP
                WHERE application_id = %s
                  AND used_at IS NULL
            """, (application_id,))

            cur.execute("""
                INSERT INTO syuwa_password_tokens (
                    application_id,
                    token_hash,
                    expires_at
                )
                VALUES (%s, %s, %s)
            """, (
                application_id,
                token_hash,
                expires_at
            ))

        conn.commit()
        return token

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def complete_syuwa_password_setup(token, password):
    from werkzeug.security import generate_password_hash

    if not token or not re.fullmatch(r"[A-Za-z0-9]{6}", password):
        return False

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    password_hash = generate_password_hash(password)

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    t.id,
                    t.application_id
                FROM syuwa_password_tokens AS t
                JOIN syuwa_applications AS a
                  ON a.id = t.application_id
                WHERE t.token_hash = %s
                  AND t.used_at IS NULL
                  AND t.expires_at > CURRENT_TIMESTAMP
                  AND a.status = 'approved'
                  AND a.password_hash IS NULL
                FOR UPDATE OF t, a
            """, (token_hash,))

            result = cur.fetchone()

            if result is None:
                conn.rollback()
                return False

            token_id, application_id = result

            cur.execute("""
                UPDATE syuwa_applications
                SET password_hash = %s
                WHERE id = %s
                  AND status = 'approved'
                  AND password_hash IS NULL
            """, (
                password_hash,
                application_id
            ))

            cur.execute("""
                UPDATE syuwa_password_tokens
                SET used_at = CURRENT_TIMESTAMP
                WHERE application_id = %s
                  AND used_at IS NULL
            """, (application_id,))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_syuwa_approved_applicant(application_id):
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    applicant_name,
                    email
                FROM syuwa_applications
                WHERE id = %s
                  AND status = 'approved'
                  AND password_hash IS NULL
            """, (application_id,))

            return cur.fetchone()

    finally:
        conn.close()


def verify_syuwa_password_token(token):
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
                    FROM syuwa_password_tokens AS t
                    JOIN syuwa_applications AS a
                      ON a.id = t.application_id
                    WHERE t.token_hash = %s
                      AND t.used_at IS NULL
                      AND t.expires_at > CURRENT_TIMESTAMP
                      AND a.status = 'approved'
                      AND a.password_hash IS NULL
                )
            """, (token_hash,))

            return cur.fetchone()[0]

    finally:
        conn.close()


def authenticate_syuwa_user(applicant_name, password):
    from werkzeug.security import check_password_hash

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, password_hash
                FROM syuwa_applications
                WHERE applicant_name = %s
                  AND status = 'approved'
                  AND password_hash IS NOT NULL
            """, (applicant_name,))

            users = cur.fetchall()

            if len(users) != 1:
                return None

            user_id, password_hash = users[0]

            if not check_password_hash(password_hash, password):
                return None

            return user_id

    finally:
        conn.close()

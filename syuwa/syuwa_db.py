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
                        CHECK (status IN ('pending', 'approved', 'rejected', 'disabled'))
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
                    used_at TIMESTAMPTZ,
                    token_type VARCHAR(20) NOT NULL DEFAULT 'setup'
                        CHECK (token_type IN ('setup', 'reset'))
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS syuwa_login_failures (
                    id BIGSERIAL PRIMARY KEY,
                    application_id BIGINT NOT NULL
                        REFERENCES syuwa_applications(id),
                    ip_address VARCHAR(45),
                    failed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_syuwa_login_failures_account_time
                ON syuwa_login_failures (
                    application_id,
                    failed_at
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
                    created_at,
                    (password_hash IS NOT NULL) AS password_set
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


def update_syuwa_account_enabled(application_id, enabled):
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            
            if enabled:
                cur.execute("""
                    UPDATE syuwa_applications
                    SET status = 'approved'
                    WHERE id = %s
                      AND status = 'disabled'
                      AND password_hash IS NOT NULL
                    RETURNING id
                """, (application_id,))

                if cur.fetchone() is None:
                    conn.rollback()
                    return False

                cur.execute("""
                    DELETE FROM syuwa_login_failures
                    WHERE application_id = %s
                """, (application_id,))

                conn.commit()
                return True

            else:

                cur.execute("""
                    UPDATE syuwa_applications
                    SET status = 'disabled'
                    WHERE id = %s
                      AND status = 'approved'
                      AND password_hash IS NOT NULL
                    RETURNING id
                """, (application_id,))

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
                  AND t.token_type = 'setup'
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
                      AND t.token_type = 'setup'
                      AND t.used_at IS NULL
                      AND t.expires_at > CURRENT_TIMESTAMP
                      AND a.status = 'approved'
                      AND a.password_hash IS NULL
                )
            """, (token_hash,))

            return cur.fetchone()[0]
    
    finally:
        conn.close()


def is_syuwa_user_active(user_id):
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM syuwa_applications
                    WHERE id = %s
                      AND status = 'approved'
                      AND password_hash IS NOT NULL
                )
            """, (user_id,))

            return cur.fetchone()[0]

    finally:
        conn.close()


def is_syuwa_account_disabled(applicant_name, password):
    from werkzeug.security import check_password_hash

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT password_hash
                FROM syuwa_applications
                WHERE applicant_name = %s
                  AND status = 'disabled'
                  AND password_hash IS NOT NULL
            """, (applicant_name,))

            user = cur.fetchone()

            if user is None:
                return False

            return check_password_hash(user[0], password)

    finally:
        conn.close()


def record_syuwa_login_failure(applicant_name, ip_address):
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM syuwa_applications
                WHERE applicant_name = %s
                  AND status = 'approved'
                  AND password_hash IS NOT NULL
                FOR UPDATE
            """, (applicant_name,))

            users = cur.fetchall()

            if len(users) != 1:
                conn.rollback()
                return False

            application_id = users[0][0]

            cur.execute("""
                INSERT INTO syuwa_login_failures (
                    application_id,
                    ip_address
                )
                VALUES (%s, %s)
            """, (application_id, ip_address))

            cur.execute("""
                SELECT COUNT(*)
                FROM syuwa_login_failures
                WHERE application_id = %s
                  AND failed_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
            """, (application_id,))

            failure_count = cur.fetchone()[0]

            if failure_count >= 5:
                cur.execute("""
                    UPDATE syuwa_applications
                    SET status = 'disabled'
                    WHERE id = %s
                      AND status = 'approved'
                """, (application_id,))

        conn.commit()

        return failure_count >= 5

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def is_syuwa_account_disabled(applicant_name, password):
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


def get_syuwa_duplicate_applicant_names():
    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT applicant_name, COUNT(*)
                FROM syuwa_applications
                GROUP BY applicant_name
                HAVING COUNT(*) > 1
                ORDER BY applicant_name
            """)

            return cur.fetchall()

    finally:
        conn.close()


def get_syuwa_password_reset_applicant(application_id):
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
                  AND password_hash IS NOT NULL
            """, (application_id,))

            return cur.fetchone()

    finally:
        conn.close()


def create_syuwa_password_reset_token(application_id):
    token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    conn = get_syuwa_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM syuwa_applications
                WHERE id = %s
                  AND status = 'approved'
                  AND password_hash IS NOT NULL
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
                    expires_at,
                    token_type
                )
                VALUES (%s, %s, %s, %s)
            """, (
                application_id,
                token_hash,
                expires_at,
                "reset"
            ))

        conn.commit()
        return token

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def verify_syuwa_password_reset_token(token):
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
                      AND t.token_type = 'reset'
                      AND t.used_at IS NULL
                      AND t.expires_at > CURRENT_TIMESTAMP
                      AND a.status = 'approved'
                      AND a.password_hash IS NOT NULL

                )
            """, (token_hash,))

            return cur.fetchone()[0]

    finally:
        conn.close()


def complete_syuwa_password_reset(token, password):
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
                  AND t.token_type = 'reset'
                  AND t.used_at IS NULL
                  AND t.expires_at > CURRENT_TIMESTAMP
                  AND a.status = 'approved'
                  AND a.password_hash IS NOT NULL
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
                  AND password_hash IS NOT NULL
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

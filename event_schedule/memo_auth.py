import os
import secrets
import psycopg2

from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")

memo_auth_bp = Blueprint(
    "memo_auth",
    __name__
)

def generate_login_code():
    return f"{secrets.randbelow(1000000):06d}"

def save_login_code(email, code, ip_address):
    code_hash = generate_password_hash(code)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO schedule_memo_login_codes (
                email,
                code_hash,
                expires_at,
                request_ip
            )
            VALUES (
                %s,
                %s,
                CURRENT_TIMESTAMP + INTERVAL '10 minutes',
                %s
            )
        """, (email, code_hash, ip_address))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

def send_login_code(email, code):
    import resend

    resend.api_key = os.environ.get("RESEND_API_KEY")

    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEYが設定されていません")

    response = resend.Emails.send({
        "from": os.environ.get("RESEND_FROM_EMAIL"),
        "to": [email],
        "subject": "【イベスケ】ログイン認証コード",
        "text": (
            "イベスケのログイン認証コードをお知らせします。\n\n"
            f"認証コード：{code}\n\n"
            "有効期限は10分間です。\n\n"
            "このメールに心当たりがない場合は、"
            "何もせず破棄してください。"
        )
    })

    return response

def can_issue_login_code(email):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                COUNT(*) FILTER (
                    WHERE created_at > CURRENT_TIMESTAMP
                        - INTERVAL '1 minute'
                ),
                COUNT(*) FILTER (
                    WHERE created_at > CURRENT_TIMESTAMP
                        - INTERVAL '1 hour'
                )
            FROM schedule_memo_login_codes
            WHERE email = %s
              AND created_at > CURRENT_TIMESTAMP
                  - INTERVAL '1 hour'
        """, (email,))

        minute_count, hour_count = cur.fetchone()

        return minute_count == 0 and hour_count < 5

    finally:
        cur.close()
        conn.close()

def normalize_login_email(email):
    if not isinstance(email, str):
        return None

    email = email.strip().lower()

    if not email or len(email) > 254:
        return None

    if email.count("@") != 1:
        return None

    local_part, domain = email.rsplit("@", 1)

    if not local_part or not domain:
        return None

    if len(local_part) > 64:
        return None

    if "." not in domain:
        return None

    if any(char.isspace() for char in email):
        return None

    return email

def can_issue_login_code_from_ip(ip_address):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT COUNT(*)
            FROM schedule_memo_login_codes
            WHERE request_ip = %s
              AND created_at > CURRENT_TIMESTAMP
                  - INTERVAL '1 hour'
        """, (ip_address,))

        count = cur.fetchone()[0]

        return count < 20

    finally:
        cur.close()
        conn.close()

def lock_login_code_requests(cur, email, ip_address):
    cur.execute("""
        SELECT pg_advisory_xact_lock(
            hashtextextended(%s, 0)
        )
    """, ("memo_login_email:" + email,))

    cur.execute("""
        SELECT pg_advisory_xact_lock(
            hashtextextended(%s, 0)
        )
    """, ("memo_login_ip:" + ip_address,))

def check_login_code_limits(email, ip_address):
    if not can_issue_login_code(email):
        return False

    if not can_issue_login_code_from_ip(ip_address):
        return False

    return True

def check_login_code_limits_locked(cur, email, ip_address):
    cur.execute("""
        SELECT COUNT(*)
        FROM schedule_memo_login_codes
        WHERE email = %s
          AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 minute'
    """, (email,))

    if cur.fetchone()[0] >= 1:
        return False

    cur.execute("""
        SELECT COUNT(*)
        FROM schedule_memo_login_codes
        WHERE email = %s
          AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    """, (email,))

    if cur.fetchone()[0] >= 5:
        return False

    cur.execute("""
        SELECT COUNT(*)
        FROM schedule_memo_login_codes
        WHERE request_ip = %s
          AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    """, (ip_address,))

    if cur.fetchone()[0] >= 20:
        return False

    return True

def issue_login_code(email, ip_address):
    code = generate_login_code()
    code_hash = generate_password_hash(code)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # 同一メールアドレス・IPの処理をロック
        lock_login_code_requests(cur, email, ip_address)

        # ロック取得後に発行制限を確認
        if not check_login_code_limits_locked(
            cur, email, ip_address
        ):
            conn.rollback()
            return None, None

        # 同じメールアドレスの古い認証コードを無効化
        cur.execute("""
            UPDATE schedule_memo_login_codes
            SET used_at = CURRENT_TIMESTAMP
            WHERE email = %s
              AND used_at IS NULL
        """, (email,))

        # 認証コードを保存
        cur.execute("""
            INSERT INTO schedule_memo_login_codes (
                email,
                code_hash,
                expires_at,
                request_ip
            )
            VALUES (
                %s,
                %s,
                CURRENT_TIMESTAMP + INTERVAL '10 minutes',
                %s
            )
            
            RETURNING id
        """, (email, code_hash, ip_address))

        login_code_id = cur.fetchone()[0]

        conn.commit()

        return code, login_code_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

def issue_and_send_login_code(email, ip_address):
    email = normalize_login_email(email)

    if email is None:
        return "invalid_email"

    code, login_code_id = issue_login_code(email, ip_address)

    if code is None:
        return "rate_limited"

    try:
        send_login_code(email, code)

    except Exception:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE schedule_memo_login_codes
                SET used_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND used_at IS NULL
            """, (login_code_id,))

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            cur.close()
            conn.close()

        raise

    return "sent"

def verify_login_code(email, code):
    email = normalize_login_email(email)

    if email is None:
        return False

    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return False

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, code_hash, attempt_count
            FROM schedule_memo_login_codes
            WHERE email = %s
              AND used_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            FOR UPDATE
        """, (email,))

        record = cur.fetchone()

        if record is None:
            conn.rollback()
            return False

        record_id, code_hash, attempt_count = record

        if attempt_count >= 5:
            conn.rollback()
            return False

        if not check_password_hash(code_hash, code):
            cur.execute("""
                UPDATE schedule_memo_login_codes
                SET attempt_count = attempt_count + 1
                WHERE id = %s
            """, (record_id,))

            conn.commit()
            return False

        cur.execute("""
            UPDATE schedule_memo_login_codes
            SET used_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (record_id,))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

def get_or_create_memo_user(email):
    email = normalize_login_email(email)

    if email is None:
        return None

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO schedule_memo_users (email)
            VALUES (%s)
            ON CONFLICT (email)
            DO UPDATE SET
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (email,))

        user_id = cur.fetchone()[0]

        conn.commit()

        return user_id

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

def login_memo_user(email):
    email = normalize_login_email(email)

    if email is None:
        return False

    user_id = get_or_create_memo_user(email)

    if user_id is None:
        return False

    session["memo_user_id"] = user_id
    session["memo_user_email"] = email

    return True

def logout_memo_user():
    session.pop("memo_user_id", None)
    session.pop("memo_user_email", None)

    return True

def is_memo_logged_in():
    return session.get("memo_user_id") is not None

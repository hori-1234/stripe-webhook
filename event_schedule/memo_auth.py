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

def check_login_code_limits(email, ip_address):
    if not can_issue_login_code(email):
        return False

    if not can_issue_login_code_from_ip(ip_address):
        return False

    return True

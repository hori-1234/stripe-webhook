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

def save_login_code(email, code):
    code_hash = generate_password_hash(code)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO schedule_memo_login_codes (
                email,
                code_hash,
                expires_at
            )
            VALUES (
                %s,
                %s,
                CURRENT_TIMESTAMP + INTERVAL '10 minutes'
            )
        """, (email, code_hash))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
        

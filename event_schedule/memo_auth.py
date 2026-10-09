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

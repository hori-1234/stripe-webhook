import os
import psycopg2

from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, Response

def create_qr_login_attempts_table():
    database_url = os.environ.get("DATABASE_URL")

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS qr_login_attempts (
            ip_address TEXT PRIMARY KEY,
            failed_count INTEGER NOT NULL DEFAULT 0,
            locked_until TIMESTAMPTZ
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

def admin_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        username = os.environ.get("ADMIN_USERNAME")
        password = os.environ.get("ADMIN_PASSWORD")

        auth = request.authorization

        if (
            not auth
            or auth.username != username
            or auth.password != password
        ):
            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証がキャンセルされました。<br><br>
                    画面を閉じてください。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="unei-yomitori"'
                }
            )

        return func(*args, **kwargs)

    return decorated

def qr_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        username = os.environ.get("QRcode_USERNAME")
        password = os.environ.get("QRcode_PASSWORD")

        # Render経由でも利用者のIPを取得する
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ip = ip.split(",")[0].strip()

        create_qr_login_attempts_table()

        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute(
            """
            SELECT failed_count, locked_until
            FROM qr_login_attempts
            WHERE ip_address = %s
            """,
            (ip,)
        )

        attempt = cur.fetchone()

        cur.close()
        conn.close()

        if attempt:
            failed_count, locked_until = attempt

            if locked_until and datetime.now(timezone.utc) < locked_until:
                return Response(
                    """
                    <div style="font-size:32px; text-align:center; margin-top:80px;">
                        ログイン試行回数を超えました。<br><br>
                        30分間ログインできません。
                    </div>
                    """,
                    403
                )
                
            # 30分経過していたら失敗履歴をリセット
            if locked_until and datetime.now(timezone.utc) >= locked_until:
                conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
                cur = conn.cursor()

                cur.execute(
                    """
                    DELETE FROM qr_login_attempts
                    WHERE ip_address = %s
                    """,
                    (ip,)
                )

                conn.commit()
                cur.close()
                conn.close()

        auth = request.authorization

        # 初回アクセス時はまだ認証情報がないため、
        # 失敗回数にはカウントせずBasic認証画面を表示する
        if not auth:
            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証が必要です。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="QRcode"'
                }
            )

        if (
            auth.username != username
            or auth.password != password
        ):
            conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
            cur = conn.cursor()
        
            cur.execute(
                """
                INSERT INTO qr_login_attempts (
                    ip_address,
                    failed_count,
                    locked_until
                )
                VALUES (%s, 1, NULL)
                ON CONFLICT (ip_address)
                DO UPDATE SET
                    failed_count = qr_login_attempts.failed_count + 1
                RETURNING failed_count
                """,
                (ip,)
            )

            failed_count = cur.fetchone()[0]

            if failed_count >= 3:
                locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

                cur.execute(
                    """
                    UPDATE qr_login_attempts
                    SET locked_until = %s
                    WHERE ip_address = %s
                    """,
                    (locked_until, ip)
                )

            conn.commit()
            cur.close()
            conn.close()

            if failed_count >= 3:
                return Response(
                    """
                    <div style="font-size:32px; text-align:center; margin-top:80px;">
                        ログイン試行回数を超えました。<br><br>
                        30分間ログインできません。
                    </div>
                    """,
                    403
                )

            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証に失敗しました。<br><br>
                    画面を閉じてください。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="QRcode"'
                }
            )

        # 認証成功時は、このIPの失敗履歴をリセットする
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute(
            """
            DELETE FROM qr_login_attempts
            WHERE ip_address = %s
            """,
            (ip,)
        )

        conn.commit()
        cur.close()
        conn.close()

        return func(*args, **kwargs)
    
    return decorated


def member_required(func):

    @wraps(func)
    def decorated(*args, **kwargs):

        username = os.environ.get("kuri_USERNAME")
        password = os.environ.get("kuri_PASSWORD")

        auth = request.authorization

        if (
            not auth
            or auth.username != username
            or auth.password != password
        ):
            
            return Response(
                """
                <div style="font-size:32px; text-align:center; margin-top:80px;">
                    認証がキャンセルされました。<br><br>
                    画面を閉じてください。
                </div>
                """,
                401,
                {
                    "WWW-Authenticate":
                    'Basic realm="member-video"'
                }
            )

        return func(*args, **kwargs)

    return decorated

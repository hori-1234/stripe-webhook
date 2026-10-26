import os
import psycopg2

from flask import Blueprint, render_template
from satsueidance.koukoku.database import create_koukoku_tables

DATABASE_URL = os.environ.get("DATABASE_URL")

satsueidance_bp = Blueprint(
    "satsueidance",
    __name__,
    template_folder="templates",
    url_prefix="/satsueidance"
)


def create_satsueidance_stats_tables():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS satsueidance_page_views (
                view_date DATE NOT NULL PRIMARY KEY,
                view_count INTEGER NOT NULL DEFAULT 0
            )
        """)


        cur.execute("""
            CREATE TABLE IF NOT EXISTS satsueidance_unique_visitors (
                visit_date DATE NOT NULL,
                visitor_id TEXT NOT NULL,
                PRIMARY KEY (visit_date, visitor_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS satsueidance_usage_sessions (
                session_id TEXT PRIMARY KEY,
                visitor_id TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                active_seconds INTEGER NOT NULL DEFAULT 0,
                last_reported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        
    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    create_koukoku_tables()


@satsueidance_bp.route("/")
def satsueidance_index():
    import secrets
    from flask import request, make_response
    from event_schedule.memo_auth import is_schedule_operator

    visitor_id = request.cookies.get("satsueidance_visitor_id")

    if not visitor_id:
        visitor_id = secrets.token_urlsafe(32)

    if not is_schedule_operator():
        create_satsueidance_stats_tables()

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO satsueidance_page_views (
                    view_date,
                    view_count
                )
                VALUES (
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date,
                    1
                )
                ON CONFLICT (view_date)
                DO UPDATE SET
                    view_count = satsueidance_page_views.view_count + 1
            """)

            cur.execute("""
                INSERT INTO satsueidance_unique_visitors (
                    visit_date,
                    visitor_id
                )
                VALUES (
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date,
                    %s
                )
                ON CONFLICT (visit_date, visitor_id)
                DO NOTHING
            """, (visitor_id,))

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            cur.close()
            conn.close()

    response = make_response(render_template("index.html"))

    response.set_cookie(
        "satsueidance_visitor_id",
        visitor_id,
        max_age=60 * 60 * 24 * 365,
        secure=request.is_secure,
        httponly=True,
        samesite="Lax"
    )

    return response


    return response


@satsueidance_bp.route("/usage", methods=["POST"])
def satsueidance_usage():
    from flask import request, jsonify
    from event_schedule.memo_auth import is_schedule_operator

    if is_schedule_operator():
        return jsonify({"ok": True})

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON"}), 400

    session_id = data.get("session_id")
    active_seconds = data.get("active_seconds")

    if (
        not isinstance(session_id, str)
        or not 1 <= len(session_id) <= 128
        or type(active_seconds) is not int
        or not 0 <= active_seconds <= 86400
    ):
        return jsonify({"error": "Invalid data"}), 400

    visitor_id = request.cookies.get("satsueidance_visitor_id")

    if not visitor_id:
        return jsonify({"error": "Visitor not found"}), 400

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO satsueidance_usage_sessions (
                session_id,
                visitor_id,
                active_seconds
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id)
            DO UPDATE SET
                active_seconds = GREATEST(
                    satsueidance_usage_sessions.active_seconds,
                    EXCLUDED.active_seconds
                ),
                last_reported_at = CURRENT_TIMESTAMP
            WHERE
                satsueidance_usage_sessions.visitor_id =
                EXCLUDED.visitor_id
        """, (
            session_id,
            visitor_id,
            active_seconds
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    return jsonify({"ok": True})

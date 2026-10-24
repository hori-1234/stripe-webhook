import os
import psycopg2

from flask import Blueprint, render_template

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

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


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

import os
import psycopg2

from flask import Blueprint, render_template

nanchyou_bp = Blueprint(
    "nanchyou",
    __name__,
    template_folder="templates"
)

DATABASE_URL = os.environ.get("DATABASE_URL")


def create_nanchyou_stats_tables():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nanchyou_page_views (
                view_date DATE NOT NULL PRIMARY KEY,
                view_count INTEGER NOT NULL DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS nanchyou_unique_visitors (
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


@nanchyou_bp.route("/nanchyou_live")
def nanchyou_live():
    import secrets
    from flask import request, make_response

    create_nanchyou_stats_tables()

    visitor_id = request.cookies.get("nanchyou_visitor_id")

    if not visitor_id:
        visitor_id = secrets.token_urlsafe(32)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO nanchyou_page_views (
                view_date, view_count
            )
            VALUES (
                (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date,
                1
            )
            ON CONFLICT (view_date)
            DO UPDATE SET
                view_count = nanchyou_page_views.view_count + 1
        """)

        cur.execute("""
            INSERT INTO nanchyou_unique_visitors (
                visit_date, visitor_id
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

    response = make_response(render_template("nanchyou_index.html"))

    response.set_cookie(
        "nanchyou_visitor_id",
        visitor_id,
        max_age=60 * 60 * 24 * 365,
        secure=True,
        httponly=True,
        samesite="Lax"
    )

    return response


@nanchyou_bp.route("/nanchyou_live/admin/stats")
def nanchyou_admin_stats():
    from admin_auth import admin_required

    @admin_required
    def show_stats():
        create_nanchyou_stats_tables()

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT
                    COALESCE(SUM(view_count) FILTER (
                        WHERE view_date =
                        (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date
                    ), 0),
                    COALESCE(SUM(view_count) FILTER (
                        WHERE DATE_TRUNC('month', view_date) =
                        DATE_TRUNC('month',
                            CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')
                    ), 0),
                    COALESCE(SUM(view_count), 0)
                FROM nanchyou_page_views
            """)
            today_views, month_views, total_views = cur.fetchone()

            cur.execute("""
                SELECT
                    COUNT(*) FILTER (
                        WHERE visit_date =
                        (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date
                    ),
                    COUNT(DISTINCT visitor_id) FILTER (
                        WHERE DATE_TRUNC('month', visit_date) =
                        DATE_TRUNC('month',
                            CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')
                    ),
                    COUNT(DISTINCT visitor_id)
                FROM nanchyou_unique_visitors
            """)
            today_unique, month_unique, total_unique = cur.fetchone()

        finally:
            cur.close()
            conn.close()
    
        return (
            "<h2>Lfe アクセス統計</h2>"
            f"<p>今日のPV：{today_views}</p>"
            f"<p>今月のPV：{month_views}</p>"
            f"<p>累計PV：{total_views}</p>"
            f"<p>今日のUU：{today_unique}</p>"
            f"<p>今月のUU：{month_unique}</p>"
            f"<p>累計UU：{total_unique}</p>"
        )

    return show_stats()

    return response

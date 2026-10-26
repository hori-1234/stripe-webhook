from flask import Blueprint, jsonify, request
from event_schedule.memo_auth import is_schedule_operator
from satsueidance.koukoku.chiiki import check_region_headers

koukoku_bp = Blueprint(
    "koukoku",
    __name__,
    url_prefix="/satsueidance/koukoku"
)


@koukoku_bp.route("/region-test")
def region_test():
    if not is_schedule_operator():
        return jsonify({"error": "Forbidden"}), 403

    result = check_region_headers()

    result["location_headers"] = {
        key: value
        for key, value in request.headers.items()
        if key.lower().startswith("cf-")
        and (
            "country" in key.lower()
            or "region" in key.lower()
            or "city" in key.lower()
            or "postal" in key.lower()
            or "latitude" in key.lower()
            or "longitude" in key.lower()
        )
    }

    result["ip_test"] = {
        "remote_addr": request.remote_addr,
        "x_forwarded_for": request.headers.get("X-Forwarded-For", ""),
        "x_real_ip": request.headers.get("X-Real-IP", ""),
        "cf_connecting_ip": request.headers.get("CF-Connecting-IP", "")
    }

    return jsonify(result)


@koukoku_bp.route("/stats")
def koukoku_stats():
    import os
    import psycopg2

    if not is_schedule_operator():
        return jsonify({"error": "Forbidden"}), 403

    from satsueidance.satsueidance_keiro import create_satsueidance_stats_tables

    create_satsueidance_stats_tables()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT
                device_type,
                COUNT(DISTINCT visitor_id) AS unique_visitors,
                COUNT(*) AS visitor_days
            FROM satsueidance_visitor_regions
            WHERE visit_date >=
                (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date - 29
            GROUP BY device_type
            ORDER BY unique_visitors DESC
        """)
        
        results = [
            {
                "device_type": row[0],
                "unique_visitors": row[1],
                "visitor_days": row[2]
            }
            for row in cur.fetchall()
        ]

        total_device_visitors = sum(
            item["unique_visitors"] for item in results
        )

        for item in results:
            item["percentage"] = (
                round(
                    item["unique_visitors"] / total_device_visitors * 100,
                    1
                )
                if total_device_visitors > 0
                else 0.0
            )
        
        ur.execute("""
            SELECT COALESCE(SUM(view_count), 0)
            FROM satsueidance_page_views
            WHERE view_date >=
                (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date - 29
        """)


        total_pv = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(DISTINCT visitor_id)
            FROM satsueidance_unique_visitors
            WHERE visit_date >=
                (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date - 29
        """)

        total_uu = cur.fetchone()[0]

        cur.execute("""
            SELECT
                COUNT(*),
                COALESCE(ROUND(AVG(active_seconds), 1), 0)
            FROM satsueidance_usage_sessions
            WHERE started_at >=
                ((CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date - 29)
                AT TIME ZONE 'Asia/Tokyo'
        """)

        usage_count, average_seconds = cur.fetchone()

        return jsonify({
            "period": "過去30日間",
            "pv": total_pv,
            "uu": total_uu,
            "usage_sessions": usage_count,
            "average_usage_seconds": float(average_seconds),
            "devices": results
        })


    finally:
        cur.close()
        conn.close()


@koukoku_bp.route("/dashboard")
def koukoku_dashboard():
    from flask import render_template

    if not is_schedule_operator():
        return jsonify({"error": "Forbidden"}), 403

    return render_template("koukoku_dashboard.html")

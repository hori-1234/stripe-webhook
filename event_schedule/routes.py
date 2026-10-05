import os
import psycopg2

from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ.get("DATABASE_URL")

event_schedule_bp = Blueprint(
    "event_schedule",
    __name__,
    template_folder="templates"
)

def create_event_schedule_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_schedules (
            id SERIAL PRIMARY KEY,
            event_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            location TEXT NOT NULL,
            event_name TEXT NOT NULL,
            performers TEXT,
            edit_password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()



@event_schedule_bp.route("/schedule/add", methods=["GET", "POST"])
def schedule_add():
    create_event_schedule_table()

    if request.method == "POST":
        event_date = request.form.get("event_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        location = request.form.get("location", "").strip()
        event_name = request.form.get("event_name", "").strip()
        performers = request.form.get("performers", "").strip()
        edit_password = request.form.get("edit_password", "")

        edit_password_hash = generate_password_hash(edit_password)

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO event_schedules (
                event_date,
                start_time,
                end_time,
                location,
                event_name,
                performers,
                edit_password_hash
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            event_date,
            start_time,
            end_time,
            location,
            event_name,
            performers,
            edit_password_hash
        ))

        conn.commit()
        cur.close()
        conn.close()

        return render_template(
            "schedule_add.html",
            success_message="イベントを登録しました。"
        )

    return render_template(
        "schedule_add.html",
        success_message=""
    )

@event_schedule_bp.route("/schedule")
def schedule():
    create_event_schedule_table()

    return render_template("schedule.html")

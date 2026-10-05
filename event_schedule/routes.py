import os
import psycopg2
import calendar
import jpholiday

from datetime import datetime
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
            genre TEXT,
            edit_password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        ALTER TABLE event_schedules
        ADD COLUMN IF NOT EXISTS genre TEXT
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
        genre = request.form.get("genre", "").strip()
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
                genre,
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
            genre,
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

    today = datetime.now()

    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)

    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1

    last_day = calendar.monthrange(year, month)[1]

    weekday_names = [
        "月", "火", "水", "木", "金", "土", "日"
    ]

    days = []

    for day in range(1, last_day + 1):
        date = datetime(year, month, day)

        holiday_name = jpholiday.is_holiday_name(date.date())

        days.append({
            "day": day,
            "weekday": weekday_names[date.weekday()],
            "weekday_number": date.weekday(),
            "holiday_name": holiday_name
        })

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            event_date,
            start_time,
            end_time,
            location,
            event_name,
            genre,
            performers
        FROM event_schedules
        WHERE EXTRACT(YEAR FROM event_date) = %s
          AND EXTRACT(MONTH FROM event_date) = %s
        ORDER BY event_date, start_time, id
    """, (year, month))

    events = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "schedule.html",
        year=year,
        month=month,
        days=days,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        events=events
    )

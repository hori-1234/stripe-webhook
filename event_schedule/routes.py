import os
import psycopg2
import calendar
import jpholiday

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

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

        if not ("08:00" <= start_time <= "23:59"):
            return "開始時間は08:00～23:59の範囲で設定してください。", 400

        if not ("08:00" <= end_time <= "23:59"):
            return "終了時間は08:00～23:59の範囲で設定してください。", 400

        if end_time <= start_time:
            return render_template(
                "schedule_add.html",
                success_message="",
                error_message="終了時間は開始時間より後に設定してください。"
            )

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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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

    display_events = []

    for event in events:
        start_time = event[2]
        end_time = event[3]

        start_minutes = (
            start_time.hour * 60
            + start_time.minute
        )

        end_minutes = (
            end_time.hour * 60
            + end_time.minute
        )

        timeline_start = 8 * 60
        timeline_end = 24 * 60
        timeline_minutes = timeline_end - timeline_start

        left_percent = (
            (start_minutes - timeline_start)
            / timeline_minutes
            * 100
        )

        width_percent = (
            (end_minutes - start_minutes)
            / timeline_minutes
            * 100
        )

        display_events.append({
            "id": event[0],
            "event_date": event[1],
            "start_time": start_time,
            "end_time": end_time,
            "location": event[4],
            "event_name": event[5],
            "genre": event[6],
            "performers": event[7],
            "left_percent": left_percent,
            "width_percent": width_percent
        })

    return render_template(
        "schedule.html",
        year=year,
        month=month,
        days=days,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        events=display_events
    )

@event_schedule_bp.route("/schedule/edit/<int:event_id>", methods=["GET", "POST"])
def schedule_edit(event_id):
    create_event_schedule_table()

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
            performers,
            edit_password_hash
        FROM event_schedules
        WHERE id = %s
    """, (event_id,))

    event = cur.fetchone()

    cur.close()
    conn.close()

    if event is None:
        return "イベントが見つかりません。", 404

    error_message = ""

    if request.args.get("time_error") == "1":
        error_message = "終了時間は開始時間より後に設定してください。"

    if session.get(f"schedule_edit_{event_id}"):
        return render_template(
            "schedule_edit_form.html",
            event=event,
            error_message=error_message
        )

    if request.method == "POST":
        edit_password = request.form.get("edit_password", "")

        if check_password_hash(event[8], edit_password):

            session[f"schedule_edit_{event_id}"] = True

            return render_template(
                "schedule_edit_form.html",
                event=event
            )

        error_message = "編集パスワードが違います。"

    return render_template(
        "schedule_edit.html",
        event=event,
        error_message=error_message
    )

@event_schedule_bp.route("/schedule/edit/<int:event_id>/update", methods=["POST"])
def schedule_edit_update(event_id):
    create_event_schedule_table()

    if not session.get(f"schedule_edit_{event_id}"):
        return "編集権限がありません。", 403

    event_date = request.form.get("event_date")
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    if not ("08:00" <= start_time <= "23:59"):
        return "開始時間は08:00～23:59の範囲で設定してください。", 400

    if not ("08:00" <= end_time <= "23:59"):
        return "終了時間は08:00～23:59の範囲で設定してください。", 400

    if end_time <= start_time:
        return redirect(
            url_for(
                "event_schedule.schedule_edit",
                event_id=event_id,
                time_error=1
            )
        )

    location = request.form.get("location", "").strip()
    event_name = request.form.get("event_name", "").strip()
    genre = request.form.get("genre", "").strip()
    performers = request.form.get("performers", "").strip()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        UPDATE event_schedules
        SET
            event_date = %s,
            start_time = %s,
            end_time = %s,
            location = %s,
            event_name = %s,
            genre = %s,
            performers = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (
        event_date,
        start_time,
        end_time,
        location,
        event_name,
        genre,
        performers,
        event_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    session.pop(f"schedule_edit_{event_id}", None)

    return redirect(
        url_for(
            "event_schedule.schedule",
            year=event_date[:4],
            month=int(event_date[5:7])
        )
    )

@event_schedule_bp.route("/schedule/edit/<int:event_id>/delete", methods=["POST"])
def schedule_edit_delete(event_id):
    create_event_schedule_table()

    if not session.get(f"schedule_edit_{event_id}"):
        return "編集権限がありません。", 403

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT event_date
        FROM event_schedules
        WHERE id = %s
    """, (event_id,))

    event = cur.fetchone()

    if event is None:
        cur.close()
        conn.close()
        return "イベントが見つかりません。", 404

    event_date = event[0]

    cur.execute("""
        DELETE FROM event_schedules
        WHERE id = %s
    """, (event_id,))

    conn.commit()
    cur.close()
    conn.close()

    session.pop(f"schedule_edit_{event_id}", None)

    return redirect(
        url_for(
            "event_schedule.schedule",
            year=event_date.year,
            month=event_date.month
        )
    )

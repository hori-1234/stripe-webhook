import os
import psycopg2
import calendar
import jpholiday

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from admin_auth import admin_required
import unicodedata

DATABASE_URL = os.environ.get("DATABASE_URL")
EVENT_PASSWORD_KEY = os.environ.get("EVENT_PASSWORD_KEY")

event_schedule_bp = Blueprint(
    "event_schedule",
    __name__,
    template_folder="templates"
)
def encrypt_edit_password(password):
    fernet = Fernet(EVENT_PASSWORD_KEY.encode())
    return fernet.encrypt(password.encode()).decode()


def decrypt_edit_password(encrypted_password):
    if not encrypted_password:
        return ""

    fernet = Fernet(EVENT_PASSWORD_KEY.encode())
    return fernet.decrypt(encrypted_password.encode()).decode()

def performer_sort_key(name):
    normalized = unicodedata.normalize("NFKC", name)
    first = normalized[0]

    if "\u3040" <= first <= "\u309f":
        group = 0
    elif "\u30a0" <= first <= "\u30ff":
        group = 1
    elif "\u4e00" <= first <= "\u9fff":
        group = 2
    else:
        group = 3

    return (group, normalized)

def delete_old_events():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM event_schedules
            WHERE event_date < CURRENT_DATE - INTERVAL '6 months'
              AND NOT EXISTS (
                  SELECT 1
                  FROM event_schedule_blocked_ips
                  WHERE event_schedule_blocked_ips.ip_address
                        = event_schedules.registration_ip
              )
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

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

    cur.execute("""
        ALTER TABLE event_schedules
        ADD COLUMN IF NOT EXISTS edit_password_encrypted TEXT
    """)

    cur.execute("""
        ALTER TABLE event_schedules
        ADD COLUMN IF NOT EXISTS registration_ip TEXT
    """)

        # 終了時間「不明」を保存できるようにする
    cur.execute("""
        ALTER TABLE event_schedules
        ALTER COLUMN end_time DROP NOT NULL
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_schedule_blocked_ips (
            id SERIAL PRIMARY KEY,
            ip_address TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

@event_schedule_bp.route("/schedule/add", methods=["GET", "POST"])
def schedule_add():
    create_event_schedule_table()

    copy_id = request.args.get("copy_id", type=int)

    copy_event = None

    if copy_id:
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
            WHERE id = %s
        """, (copy_id,))

        copy_event = cur.fetchone()

        cur.close()
        conn.close()


    if request.method == "POST":
        event_date = request.form.get("event_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        end_time_unknown = request.form.get("end_time_unknown") == "1"

        if end_time_unknown:
            end_time = None
            
        location = request.form.get("location", "").strip()
        event_name = request.form.get("event_name", "").strip()
        genre = request.form.get("genre", "").strip()
        performers = request.form.get("performers", "").strip()
        edit_password = request.form.get("edit_password", "")

        registration_ip = request.headers.get(
            "X-Forwarded-For",
            request.remote_addr
        )
        registration_ip = registration_ip.split(",")[0].strip()

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT 1
            FROM event_schedule_blocked_ips
            WHERE ip_address = %s
        """, (registration_ip,))

        is_blocked = cur.fetchone() is not None

        cur.close()
        conn.close()

        if is_blocked:
            return "このIPアドレスからはイベントを登録できません。", 403

        if not ("08:00" <= start_time <= "23:59"):
            return "開始時間は08:00～23:59の範囲で設定してください。", 400

        if not end_time_unknown:
            if not ("08:00" <= end_time <= "23:59"):
                return "終了時間は08:00～23:59の範囲で設定してください。", 400

            if end_time <= start_time:
                return render_template(
                    "schedule_add.html",
                    success_message="",
                    error_message="終了時間は開始時間より後に設定してください。",
                    form_data=request.form
                )

        edit_password_hash = generate_password_hash(edit_password)
        edit_password_encrypted = encrypt_edit_password(edit_password)

        conn = None
        cur = None

        try:
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
                    edit_password_hash,
                    edit_password_encrypted,
                    registration_ip
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_date,
                start_time,
                end_time,
                location,
                event_name,
                genre,
                performers,
                edit_password_hash,
                edit_password_encrypted,
                registration_ip
            ))

            conn.commit()

        except Exception:
            if conn:
                conn.rollback()
            raise

        finally:
            if cur:
                cur.close()

            if conn:
                conn.close()
        
        return render_template(
            "schedule_add.html",
            success_message="イベントを登録しました。"
        )

    return render_template(
        "schedule_add.html",
        success_message="",
        copy_event=copy_event
    )

@event_schedule_bp.route("/schedule")
def schedule():
    create_event_schedule_table()
    delete_old_events()

    today = datetime.now()

    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    genre = request.args.get("genre", "").strip()
    selected_locations = request.args.getlist("location")
    event_name_keyword = request.args.get("event_name", "").strip()
    performer_keyword = request.args.get("performer", "").strip()

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

    query = """
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
    """
    if performer_keyword:
        query += " WHERE event_date >= CURRENT_DATE"
        params = []
    else:
        query += """
            WHERE EXTRACT(YEAR FROM event_date) = %s
              AND EXTRACT(MONTH FROM event_date) = %s
        """
        params = [year, month]
    
    if genre:
        query += " AND genre = %s"
        params.append(genre)

    if selected_locations:
        placeholders = ", ".join(
            ["%s"] * len(selected_locations)
        )
        query += f" AND location IN ({placeholders})"
        params.extend(selected_locations)

    if event_name_keyword:
        query += " AND event_name ILIKE %s"
        params.append(f"%{event_name_keyword}%")

    if performer_keyword:
        query += " AND performers ILIKE %s"
        params.append(f"%{performer_keyword}%")

    query += " ORDER BY event_date, start_time, id"

    cur.execute(query, params)
    
    events = cur.fetchall()

    performer_query = """
        SELECT performers
        FROM event_schedules
        WHERE event_date >= CURRENT_DATE
          AND performers IS NOT NULL
          AND performers <> ''
    """

    performer_params = []

    if genre:
        performer_query += " AND genre = %s"
        performer_params.append(genre)

    if selected_locations:
        placeholders = ", ".join(
            ["%s"] * len(selected_locations)
        )
        performer_query += f" AND location IN ({placeholders})"
        performer_params.extend(selected_locations)

    if event_name_keyword:
        performer_query += " AND event_name ILIKE %s"
        performer_params.append(f"%{event_name_keyword}%")

    cur.execute(performer_query, performer_params)
    performer_rows = cur.fetchall()

    registered_performers = set()

    for row in performer_rows:
        for performer in row[0].splitlines():
            performer = performer.strip()

            if performer:
                registered_performers.add(performer)
                
    registered_performers = sorted(
        registered_performers,
        key=performer_sort_key
    )
    
    # 表示中の月に登録されている場所を重複なしで取得
    cur.execute("""
        SELECT DISTINCT location
        FROM event_schedules
        WHERE EXTRACT(YEAR FROM event_date) = %s
          AND EXTRACT(MONTH FROM event_date) = %s
          AND location IS NOT NULL
          AND location <> ''
        ORDER BY location
    """, (year, month))

    locations = [
        row[0] for row in cur.fetchall()
    ]

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

        if end_time is None:
            end_minutes = 24 * 60
        else:
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
    performer_search_dates = []

    if performer_keyword:
        unique_dates = sorted({
            event["event_date"]
            for event in display_events
        })

        performer_search_dates = [
            {
                "date": search_date,
                "holiday_name": jpholiday.is_holiday_name(search_date)
            }
            for search_date in unique_dates
        ]

    return render_template(
        "schedule.html",
        year=year,
        month=month,
        days=days,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        events=display_events,
        locations=locations,
        performer_search_dates=performer_search_dates,
        registered_performers=registered_performers
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
        action = request.form.get("action", "edit")

        if action == "copy":
            return redirect(
                url_for(
                    "event_schedule.schedule_add",
                    copy_id=event_id
                )
            )
            
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
    end_time_unknown = request.form.get("end_time_unknown") == "1"

    if end_time_unknown:
        end_time = None

    if not ("08:00" <= start_time <= "23:59"):
        return "開始時間は08:00～23:59の範囲で設定してください。", 400

    if not end_time_unknown:
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

    is_admin_edit = session.pop(
        f"schedule_admin_edit_{event_id}",
        False
    )

    session.pop(f"schedule_edit_{event_id}", None)

    if is_admin_edit:
        return redirect(
            url_for("event_schedule.schedule_admin")
        )

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

    is_admin_edit = session.pop(
        f"schedule_admin_edit_{event_id}",
        False
    )

    session.pop(f"schedule_edit_{event_id}", None)

    if is_admin_edit:
        return redirect(
            url_for("event_schedule.schedule_admin")
        )

    return redirect(
        url_for(
            "event_schedule.schedule",
            year=event_date.year,
            month=event_date.month
        )
    )
    
@event_schedule_bp.route("/schedule/admin")
@admin_required
def schedule_admin():
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
            edit_password_encrypted,
            registration_ip
        FROM event_schedules
        ORDER BY event_date, start_time, id
    """)

    events = cur.fetchall()

    cur.execute("""
        SELECT ip_address
        FROM event_schedule_blocked_ips
    """)

    blocked_ips = {
        row[0] for row in cur.fetchall()
    }

    cur.close()
    conn.close()

    admin_events = []

    for event in events:
        edit_password = ""

        if event[8]:
            edit_password = decrypt_edit_password(event[8])

        admin_events.append({
            "id": event[0],
            "event_date": event[1],
            "start_time": event[2],
            "end_time": event[3],
            "location": event[4],
            "event_name": event[5],
            "genre": event[6],
            "performers": event[7],
            "edit_password": edit_password,
            "registration_ip": event[9],
            "is_blocked": event[9] in blocked_ips
        })

    return render_template(
        "schedule_admin.html",
        events=admin_events
    )

@event_schedule_bp.route(
    "/schedule/admin/block-ip",
    methods=["POST"]
)
@admin_required
def schedule_admin_block_ip():
    ip_address = request.form.get("ip_address", "").strip()

    if not ip_address:
        return redirect(
            url_for("event_schedule.schedule_admin")
        )

    create_event_schedule_table()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO event_schedule_blocked_ips (
            ip_address
        )
        VALUES (%s)
        ON CONFLICT (ip_address) DO NOTHING
    """, (ip_address,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(
        url_for("event_schedule.schedule_admin")
    )

@event_schedule_bp.route(
    "/schedule/admin/unblock-ip",
    methods=["POST"]
)
@admin_required
def schedule_admin_unblock_ip():
    ip_address = request.form.get("ip_address", "").strip()

    if not ip_address:
        return redirect(
            url_for("event_schedule.schedule_admin")
        )

    create_event_schedule_table()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM event_schedule_blocked_ips
        WHERE ip_address = %s
    """, (ip_address,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(
        url_for("event_schedule.schedule_admin")
    )


@event_schedule_bp.route("/schedule/admin/edit/<int:event_id>")
@admin_required
def schedule_admin_edit(event_id):
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

    session[f"schedule_edit_{event_id}"] = True
    session[f"schedule_admin_edit_{event_id}"] = True

    return render_template(
        "schedule_edit_form.html",
        event=event,
        error_message=""
    )

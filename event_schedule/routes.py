import os
import psycopg2
import calendar
import jpholiday
import secrets

from zoneinfo import ZoneInfo
from event_schedule.memo_auth import (
    get_logged_in_memo_email,
    should_show_google_link_prompt,
    get_google_link_csrf_token
)
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from admin_auth import admin_required
import unicodedata
from .memo_db import (
    create_schedule_memo_users_table,
    create_schedule_memo_login_codes_table,
    create_schedule_memos_table,
    create_schedule_memo_alarms_table,
)

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

def create_schedule_stats_tables():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_page_views (
                view_date DATE NOT NULL,
                device_type TEXT NOT NULL,
                view_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (view_date, device_type)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_performer_clicks (
                click_date DATE NOT NULL,
                performer_name TEXT NOT NULL,
                click_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (click_date, performer_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_unique_visitors (
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
        streaming_available = request.form.get("streaming_available") == "1"
        edit_password = request.form.get("edit_password", "")

        if len(event_name) > 40:
            return render_template(
                "schedule_add.html",
                error_message="イベント名は全角・半角問わず40文字以内で入力してください。",
                form_data=request.form,
                copy_event=copy_event
            )

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
                    streaming_available,
                    edit_password_hash,
                    edit_password_encrypted,
                    registration_ip
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                event_date,
                start_time,
                end_time,
                location,
                event_name,
                genre,
                performers,
                streaming_available,
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

    visitor_id = request.cookies.get("schedule_visitor_id")

    if not visitor_id:
        visitor_id = secrets.token_urlsafe(32)

    if request.args.get("performer_refresh") != "1":
        user_agent = request.user_agent.string.lower()

        if "mobile" in user_agent or "iphone" in user_agent or "android" in user_agent:
            device_type = "スマホ"
        else:
            device_type = "PC"

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO schedule_page_views (
                view_date, device_type, view_count
            )
            VALUES (
                (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date,
                %s, 1
            )
            ON CONFLICT (view_date, device_type)
            DO UPDATE SET view_count = schedule_page_views.view_count + 1
        """, (device_type,))

        cur.execute("""
            INSERT INTO schedule_unique_visitors (
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
        cur.close()
        conn.close()

    today = datetime.now()

    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    genre = request.args.get("genre", "").strip()
    selected_locations = request.args.getlist("location")
    event_name_keyword = request.args.get("event_name", "").strip()
    performer_keyword = request.args.get("performer", "").strip()
    mymemo_mode = request.args.get("mymemo") == "1"

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
            performers,
            streaming_available
        FROM event_schedules
    """
    if performer_keyword:
        query += " WHERE event_date >= CURRENT_DATE"
        params = []
    elif mymemo_mode:
        query += " WHERE 1 = 1"
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
        for performer in row[0].split():
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

    # ログイン中のユーザーのイベントメモを取得
    saved_event_memos = {}
    saved_date_memos = {}

    memo_user_id = session.get("memo_user_id")

    if memo_user_id:
        cur.execute("""
            SELECT
                event_id,
                memo_text,
                tag,
                tag_color
            FROM schedule_memos
            WHERE user_id = %s
              AND event_id IS NOT NULL
        """, (memo_user_id,))

        for event_id, memo_text, tag, tag_color in cur.fetchall():
            saved_event_memos[event_id] = {
                "memo_text": memo_text or "",
                "tag": tag or "",
                "tag_color": tag_color or "#ffff99"
            }

        # ログイン中のユーザーの日付メモを取得
        cur.execute("""
            SELECT memo_date, memo_text, tag, tag_color
            FROM schedule_memos
            WHERE user_id = %s
              AND event_id IS NULL
        """, (memo_user_id,))
    
        for memo_date, memo_text, tag, tag_color in cur.fetchall():
            saved_date_memos[memo_date.isoformat()] = {
                "memo_text": memo_text or "",
                "tag": tag or "",
                "tag_color": tag_color or "#ffff99",
                "alarms": []
            }

        cur.execute("""
            SELECT
                m.memo_date,
                a.alarm_number,
                a.recipient_email,
                a.subject,
                a.body,
                a.scheduled_at,
                a.status
            FROM schedule_memo_alarms a
            JOIN schedule_memos m
                ON m.id = a.memo_id
            WHERE m.user_id = %s
              AND m.event_id IS NULL
              AND EXTRACT(YEAR FROM m.memo_date) = %s
              AND EXTRACT(MONTH FROM m.memo_date) = %s
            ORDER BY m.memo_date, a.alarm_number
        """, (memo_user_id, year, month))

        for (
            memo_date,
            alarm_number,
            recipient_email,
            subject,
            body,
            scheduled_at,
            status
        ) in cur.fetchall():

            date_key = memo_date.isoformat()

            if date_key not in saved_date_memos:
                continue

            if status == "sent":
                continue
                
            saved_date_memos[date_key]["alarms"].append({
                "alarm_number": alarm_number,
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body or "",
                "scheduled_at": scheduled_at.astimezone(
                    ZoneInfo("Asia/Tokyo")
                ).strftime("%Y-%m-%dT%H:%M"),
                "status": status
            })

    cur.execute("""
        SELECT COALESCE(SUM(view_count), 0)
        FROM schedule_page_views
        WHERE view_date =
            (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date
    """)

    today_views = cur.fetchone()[0]
                
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
            "streaming_available": event[8],
            "left_percent": left_percent,
            "width_percent": width_percent
        })
    performer_search_dates = []

    if performer_keyword or mymemo_mode:
        if mymemo_mode:
            unique_dates = set()

            for date_key, memo in saved_date_memos.items():
                if memo.get("memo_text") or memo.get("tag"):
                    unique_dates.add(
                        datetime.strptime(date_key, "%Y-%m-%d").date()
                    )

            for event in display_events:
                memo = saved_event_memos.get(event["id"], {})

                if memo.get("memo_text") or memo.get("tag"):
                    unique_dates.add(event["event_date"])

            unique_dates = sorted(unique_dates)
        else:
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

    response = make_response(render_template(
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
        registered_performers=registered_performers,
        saved_event_memos=saved_event_memos,
        saved_date_memos=saved_date_memos,
        today_views=today_views,
        memo_login_email=get_logged_in_memo_email(),
        show_google_link_prompt=should_show_google_link_prompt(),
        google_link_csrf_token=get_google_link_csrf_token()
    ))

    response.set_cookie(
        "schedule_visitor_id",
        visitor_id,
        max_age=60 * 60 * 24 * 365,
        secure=request.is_secure,
        httponly=True,
        samesite="Lax"
    )

    return response

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
            edit_password_hash,
            streaming_available
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
    streaming_available = request.form.get("streaming_available") == "1"
    
    if len(event_name) > 40:
        return "イベント名は全角・半角問わず40文字以内で入力してください。", 400

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
            streaming_available = %s,
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
        streaming_available,
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

@event_schedule_bp.route("/schedule/performer-click", methods=["POST"])
def schedule_performer_click():
    performer_name = request.form.get("performer", "").strip()

    if not performer_name or len(performer_name) > 200:
        return "", 400

    create_schedule_stats_tables()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO schedule_performer_clicks (
                click_date,
                performer_name,
                click_count
            )
            VALUES (
                (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date,
                %s,
                1
            )
            ON CONFLICT (click_date, performer_name)
            DO UPDATE SET click_count = schedule_performer_clicks.click_count + 1
        """, (performer_name,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    return "", 204

@event_schedule_bp.route("/schedule/admin/stats")
@admin_required
def schedule_admin_stats():
    create_schedule_stats_tables()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COALESCE(SUM(view_count) FILTER (
                WHERE view_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date
            ), 0),
            COALESCE(SUM(view_count) FILTER (
                WHERE DATE_TRUNC('month', view_date::timestamp) =
                      DATE_TRUNC('month', CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')
            ), 0),
            COALESCE(SUM(view_count), 0)
        FROM schedule_page_views
    """)

    today_views, month_views, total_views = cur.fetchone()

    cur.execute("""
        SELECT
            performer_name,
            SUM(click_count) AS total_clicks
        FROM schedule_performer_clicks
        GROUP BY performer_name
        ORDER BY total_clicks DESC, performer_name
    """)

    performer_ranking = cur.fetchall()

    cur.execute("""
        SELECT
            view_date,
            SUM(view_count) AS daily_views
        FROM schedule_page_views
        WHERE view_date >=
            (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date - 29
        GROUP BY view_date
        ORDER BY view_date DESC
    """)

    daily_views = cur.fetchall()

    cur.execute("""
        SELECT
            device_type,
            SUM(view_count) AS total_views
        FROM schedule_page_views
        GROUP BY device_type
        ORDER BY total_views DESC
    """)

    device_views = cur.fetchall()
    cur.execute("""
        SELECT
            COUNT(DISTINCT visitor_id) FILTER (
                WHERE visit_date =
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date
            ),
            COUNT(DISTINCT visitor_id) FILTER (
                WHERE visit_date >= DATE_TRUNC(
                    'month',
                    CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo'
                )::date
            ),
            COUNT(DISTINCT visitor_id)
        FROM schedule_unique_visitors
    """)

    today_unique, month_unique, total_unique = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "schedule_stats.html",
        today_views=today_views,
        month_views=month_views,
        total_views=total_views,
        performer_ranking=performer_ranking,
        daily_views=daily_views,
        device_views=device_views,
        today_unique=today_unique,
        month_unique=month_unique,
        total_unique=total_unique
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
            edit_password_hash,
            streaming_available
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

@event_schedule_bp.route("/schedule/mynote")
def schedule_mynote():

    memo_login_email = get_logged_in_memo_email()

    if not memo_login_email:
        return redirect(url_for("event_schedule.schedule"))

    return render_template(
        "schedule_mynote.html",
        memo_login_email=memo_login_email
    )

@event_schedule_bp.route("/schedule/memo/event/save", methods=["POST"])
def schedule_memo_event_save():

    user_id = session.get("memo_user_id")

    if not user_id:
        return {"error": "ログインが必要です"}, 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "送信データが正しくありません"}, 400

    event_id = data.get("event_id")
    memo_text = data.get("memo_text", "")
    tag = data.get("tag", "")
    tag_color = data.get("tag_color", "#ffff99")

    if type(event_id) is not int or event_id <= 0:
        return {"error": "イベントIDが正しくありません"}, 400

    if not all(isinstance(value, str) for value in (
        memo_text, tag, tag_color
    )):
        return {"error": "メモの入力値が正しくありません"}, 400

    if len(memo_text) > 10000:
        return {"error": "メモは10000文字以内にしてください"}, 400

    if tag not in ("", "参加", "検討中", "チケ発", "事前準備", "練習"):
        return {"error": "付箋の種類が正しくありません"}, 400

    import re

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", tag_color):
        return {"error": "付箋の色が正しくありません"}, 400

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT event_date, event_name, location
            FROM event_schedules
            WHERE id = %s
        """, (event_id,))

        event = cur.fetchone()

        if event is None:
            return {"error": "イベントが見つかりません"}, 404

        event_date, event_name, event_location = event

        cur.execute("""
            INSERT INTO schedule_memos (
                user_id,
                event_id,
                memo_date,
                event_name,
                event_location,
                memo_text,
                tag,
                tag_color
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, event_id)
                WHERE event_id IS NOT NULL
            DO UPDATE SET
                memo_date = EXCLUDED.memo_date,
                event_name = EXCLUDED.event_name,
                event_location = EXCLUDED.event_location,
                memo_text = EXCLUDED.memo_text,
                tag = EXCLUDED.tag,
                tag_color = EXCLUDED.tag_color,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            user_id,
            event_id,
            event_date,
            event_name,
            event_location,
            memo_text,
            tag,
            tag_color
        ))

        memo_id = cur.fetchone()[0]
        conn.commit()

        return {"success": True, "memo_id": memo_id}

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

def create_schedule_memo_alarms_table():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schedule_memo_alarms (
                id BIGSERIAL PRIMARY KEY,

                memo_id BIGINT NOT NULL
                    REFERENCES schedule_memos(id)
                    ON DELETE CASCADE,

                alarm_number INTEGER NOT NULL
                    CHECK (alarm_number BETWEEN 1 AND 4),

                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',

                scheduled_at TIMESTAMPTZ NOT NULL,

                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending',
                        'processing',
                        'sent',
                        'failed',
                        'cancelled'
                    )),

                sent_at TIMESTAMPTZ,
                attempt_count INTEGER NOT NULL DEFAULT 0,

                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT schedule_memo_alarms_number_unique
                    UNIQUE (memo_id, alarm_number)
            )
        """)

        cur.execute("""
            ALTER TABLE schedule_memo_alarms
            ADD COLUMN IF NOT EXISTS alarm_number INTEGER
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_schedule_memo_alarms_memo_number
            ON schedule_memo_alarms (memo_id, alarm_number)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_schedule_memo_alarms_pending
            ON schedule_memo_alarms (scheduled_at)
            WHERE status = 'pending'
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

@event_schedule_bp.route("/schedule/memo/date/save", methods=["POST"])
def schedule_memo_date_save():

    from datetime import timezone
    from zoneinfo import ZoneInfo

    user_id = session.get("memo_user_id")

    if not user_id:
        return {"error": "ログインが必要です"}, 401

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "送信データが正しくありません"}, 400

    memo_date = data.get("memo_date")
    memo_text = data.get("memo_text", "")
    tag = data.get("tag", "")
    tag_color = data.get("tag_color", "#ffff99")
    alarms = data.get("alarms", [])

    if not isinstance(memo_date, str):
        return {"error": "日付が正しくありません"}, 400

    if not all(isinstance(value, str) for value in (
        memo_text, tag, tag_color
    )):
        return {"error": "入力値が正しくありません"}, 400

    try:
        parsed_date = datetime.strptime(
            memo_date, "%Y-%m-%d"
        ).date()
    except ValueError:
        return {"error": "日付が正しくありません"}, 400

    if len(memo_text) > 10000:
        return {"error": "メモは10000文字以内にしてください"}, 400

    if not isinstance(alarms, list) or len(alarms) > 4:
        return {"error": "アラームは4件までです"}, 400

    parsed_alarms = []
    used_numbers = set()

    # 1日あたりのメール通知予約上限
    DAILY_ALARM_RESERVATION_LIMIT = 90

    def get_daily_alarm_reservation_count(
        cur, target_date, memo_id, alarm_numbers
    ):
        # 予約中・送信処理中の件数を取得
        cur.execute("""
            SELECT COUNT(*)
            FROM schedule_memo_alarms
            WHERE status IN ('pending', 'processing')
              AND (scheduled_at AT TIME ZONE 'Asia/Tokyo')::date = %s
              AND NOT (
                  memo_id = %s
                  AND alarm_number = ANY(%s)
                  AND status = 'pending'
              )
        """, (
            target_date,
            memo_id,
            alarm_numbers
        ))

        reserved_count = cur.fetchone()[0]

        # 送信履歴テーブルの存在を確認
        cur.execute("""
            SELECT to_regclass(
                'public.schedule_memo_alarm_send_history'
            )
        """)

        history_table = cur.fetchone()[0]

        sent_count = 0

        if history_table is not None:
            cur.execute("""
                SELECT COUNT(*)
                FROM schedule_memo_alarm_send_history
                WHERE (sent_at AT TIME ZONE 'Asia/Tokyo')::date = %s
            """, (target_date,))

            sent_count = cur.fetchone()[0]

        return reserved_count + sent_count

    for alarm in alarms:

        if not isinstance(alarm, dict):
            return {"error": "アラームの形式が正しくありません"}, 400

        alarm_number = alarm.get("alarm_number")
        recipient_email = alarm.get("recipient_email")
        subject = alarm.get("subject")
        body = alarm.get("body", "")
        scheduled_at = alarm.get("scheduled_at")

        if type(alarm_number) is not int or not 1 <= alarm_number <= 4:
            return {"error": "アラーム番号が正しくありません"}, 400

        if alarm_number in used_numbers:
            return {"error": "アラーム番号が重複しています"}, 400

        used_numbers.add(alarm_number)

        if not all(isinstance(value, str) for value in (
            recipient_email, subject, body, scheduled_at
        )):
            return {"error": "アラームの入力値が正しくありません"}, 400

        recipient_email = recipient_email.strip()
        subject = subject.strip()

        if (
            not recipient_email
            or "@" not in recipient_email
            or not subject
            or not scheduled_at
        ):
            return {"error": "アラームの必須項目を入力してください"}, 400

        try:
            alarm_datetime = datetime.strptime(
                scheduled_at, "%Y-%m-%dT%H:%M"
            ).replace(tzinfo=ZoneInfo("Asia/Tokyo"))

        except ValueError:
            return {"error": "アラーム日時が正しくありません"}, 400

        if alarm_datetime <= datetime.now(timezone.utc):
            return {"error": "アラーム日時は未来にしてください"}, 400

        parsed_alarms.append((
            alarm_number,
            recipient_email,
            subject,
            body,
            alarm_datetime
        ))

    create_schedule_memo_alarms_table()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO schedule_memos (
                user_id,
                event_id,
                memo_date,
                memo_text,
                tag,
                tag_color
            )
            VALUES (%s, NULL, %s, %s, %s, %s)
            ON CONFLICT (user_id, memo_date)
                WHERE event_id IS NULL
            DO UPDATE SET
                memo_text = EXCLUDED.memo_text,
                tag = EXCLUDED.tag,
                tag_color = EXCLUDED.tag_color,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (
            user_id,
            parsed_date,
            memo_text,
            tag,
            tag_color
        ))

        memo_id = cur.fetchone()[0]

        # 同時予約による上限超過を防ぐ
        cur.execute("""
            SELECT pg_advisory_xact_lock(20261010, 1)
        """)

        # 今回保存するアラーム番号
        alarm_numbers = [
            alarm[0] for alarm in parsed_alarms
        ]

        # 通知日ごとに予約数を確認
        alarm_dates = {
            alarm[4].date() for alarm in parsed_alarms
        }

        for target_date in alarm_dates:

            existing_count = get_daily_alarm_reservation_count(
                cur,
                target_date,
                memo_id,
                alarm_numbers
            )

            # 同じ日付で予約済みのアラーム番号を取得
            cur.execute("""
                SELECT alarm_number
                FROM schedule_memo_alarms
                WHERE memo_id = %s
                  AND status = 'pending'
                  AND (scheduled_at AT TIME ZONE 'Asia/Tokyo')::date = %s
            """, (memo_id, target_date))

            existing_alarm_numbers = {
                row[0] for row in cur.fetchall()
            }

            # 今回保存するアラームを日付ごとに数える
            new_count = sum(
                1 for alarm in parsed_alarms
                if alarm[4].date() == target_date
            )

            if existing_count + new_count > DAILY_ALARM_RESERVATION_LIMIT:
                conn.rollback()
                return {
                    "error": (
                        "ご指定の日付は、メール通知の予約が上限に達しているため、"
                        "新たに設定できません。恐れ入りますが、"
                        "別の日付をご指定ください。"
                    )
                }, 409

        for (
            alarm_number,
            recipient_email,
            subject,
            body,
            alarm_datetime
        ) in parsed_alarms:

            cur.execute("""
                INSERT INTO schedule_memo_alarms (
                    memo_id,
                    alarm_number,
                    recipient_email,
                    subject,
                    body,
                    scheduled_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (memo_id, alarm_number)
                DO UPDATE SET
                    recipient_email = EXCLUDED.recipient_email,
                    subject = EXCLUDED.subject,
                    body = EXCLUDED.body,
                    scheduled_at = EXCLUDED.scheduled_at,
                    status = 'pending',
                    sent_at = NULL,
                    attempt_count = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE schedule_memo_alarms.status IN ('sent', 'cancelled')
                   OR schedule_memo_alarms.recipient_email IS DISTINCT FROM EXCLUDED.recipient_email
                   OR schedule_memo_alarms.subject IS DISTINCT FROM EXCLUDED.subject
                   OR schedule_memo_alarms.body IS DISTINCT FROM EXCLUDED.body
                   OR schedule_memo_alarms.scheduled_at IS DISTINCT FROM EXCLUDED.scheduled_at
            """, (
                memo_id,
                alarm_number,
                recipient_email,
                subject,
                body,
                alarm_datetime
            ))

        conn.commit()

        return {
            "success": True,
            "memo_id": memo_id
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

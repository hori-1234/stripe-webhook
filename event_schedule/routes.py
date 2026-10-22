import os
import psycopg2
import calendar
import jpholiday
import secrets
import subprocess
import tempfile
import shutil

from .flyer_storage import (
    upload_flyer_to_r2,
    delete_flyer_from_r2,
    get_flyer_url
)
from zoneinfo import ZoneInfo
from event_schedule.memo_auth import (
    get_logged_in_memo_email,
    should_show_google_link_prompt,
    get_google_link_csrf_token
)
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from admin_auth import admin_required
import unicodedata
from .memo_db import (
    create_schedule_memo_users_table,
    create_schedule_memo_login_codes_table,
    create_schedule_memos_table,
    create_schedule_memo_alarms_table,
    create_schedule_favorite_performers_table,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
EVENT_PASSWORD_KEY = os.environ.get("EVENT_PASSWORD_KEY")

event_schedule_bp = Blueprint(
    "event_schedule",
    __name__,
    template_folder="templates"
)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://"
)


def encrypt_edit_password(password):
    fernet = Fernet(EVENT_PASSWORD_KEY.encode())
    return fernet.encrypt(password.encode()).decode()


def decrypt_edit_password(encrypted_password):
    if not encrypted_password:
        return ""

    fernet = Fernet(EVENT_PASSWORD_KEY.encode())
    return fernet.decrypt(encrypted_password.encode()).decode()


def clean_performer_text(text):
    return "".join(
        char for char in text
        if unicodedata.category(char) != "Cf"
    )

def performer_sort_key(name):
    normalized = unicodedata.normalize(
        "NFKC",
        clean_performer_text(name).strip()
    )

    if not normalized:
        return (4, "")

    first = normalized[0]

    if "\u3040" <= first <= "\u309f":
        group = 0
    elif "\u30a0" <= first <= "\u30ff":
        group = 1
    elif "\u4e00" <= first <= "\u9fff":
        group = 2
    elif first.isascii() and first.isalnum():
        group = 3
    else:
        group = 4

    return (group, normalized.casefold())


def delete_old_events():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # 開催日から2か月経過したフライヤーを取得
        cur.execute("""
            SELECT
                id,
                flyer_thumbnail_key,
                flyer_image_key
            FROM event_schedules
            WHERE event_date < CURRENT_DATE - INTERVAL '2 months'
              AND (
                  flyer_thumbnail_key IS NOT NULL
                  OR flyer_image_key IS NOT NULL
              )
        """)

        expired_flyers = cur.fetchall()

        # R2から削除できた画像だけ、DBの画像キーをNULLにする
        for event_id, thumbnail_key, image_key in expired_flyers:
            try:
                delete_flyer_from_r2(thumbnail_key, image_key)

                cur.execute("""
                    UPDATE event_schedules
                    SET
                        flyer_thumbnail_key = NULL,
                        flyer_image_key = NULL
                    WHERE id = %s
                """, (event_id,))

                conn.commit()

            except Exception as e:
                conn.rollback()
                print(
                    f"フライヤー自動削除失敗: "
                    f"event_id={event_id}, error={e}"
                )

        # 開催日から6か月経過したイベントを削除
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
        ADD COLUMN IF NOT EXISTS flyer_thumbnail_key TEXT
    """)

    cur.execute("""
        ALTER TABLE event_schedules
        ADD COLUMN IF NOT EXISTS flyer_image_key TEXT
    """)    

    cur.execute("""
        ALTER TABLE event_schedules
        ADD COLUMN IF NOT EXISTS organizer_sns_url TEXT
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
        performers = clean_performer_text(
            request.form.get("performers", "")
        ).strip()

        organizer_sns_url = request.form.get("organizer_sns_url", "").strip()
        streaming_available = request.form.get("streaming_available") == "1"
        edit_password = request.form.get("edit_password", "")

        if organizer_sns_url:
            from urllib.parse import urlsplit

            try:
                parsed_url = urlsplit(organizer_sns_url)
                valid_url = (
                    parsed_url.scheme == "https"
                    and bool(parsed_url.hostname)
                    and not parsed_url.username
                    and not parsed_url.password
                    and not any(char.isspace() for char in organizer_sns_url)
                    and len(organizer_sns_url) <= 500
                )
            except ValueError:
                valid_url = False

            if not valid_url:
                return render_template(
                    "schedule_add.html",
                    error_message="主催者SNSには有効なHTTPSのURLを入力してください（500文字以内）。",
                    form_data=request.form,
                    copy_event=copy_event
                ), 400

        flyer_file = request.files.get("flyer_image")

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
        flyer_thumbnail_key = None
        flyer_image_key = None
        db_committed = False

        try:
            # フライヤー画像が選択されている場合のみアップロード
            if flyer_file and flyer_file.filename:
                flyer_thumbnail_key, flyer_image_key = upload_flyer_to_r2(
                    flyer_file
                )

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
                    organizer_sns_url,
                    streaming_available,
                    edit_password_hash,
                    edit_password_encrypted,
                    registration_ip,
                    flyer_thumbnail_key,
                    flyer_image_key
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                event_date,
                start_time,
                end_time,
                location,
                event_name,
                genre,
                performers,
                organizer_sns_url,
                streaming_available,
                edit_password_hash,
                edit_password_encrypted,
                registration_ip,
                flyer_thumbnail_key,
                flyer_image_key
            ))


            conn.commit()
            db_committed = True

        except ValueError as e:
            if conn:
                conn.rollback()

            if flyer_thumbnail_key or flyer_image_key:
                delete_flyer_from_r2(
                    flyer_thumbnail_key,
                    flyer_image_key
                )

            return render_template(
                "schedule_add.html",
                error_message=str(e),
                form_data=request.form,
                copy_event=copy_event
            ), 400

        except Exception:
            if conn:
                conn.rollback()

            # DB登録に失敗した場合、R2の画像も削除
            if not db_committed and (flyer_thumbnail_key or flyer_image_key):
                try:
                    delete_flyer_from_r2(
                        flyer_thumbnail_key,
                        flyer_image_key
                    )
                except Exception:
                    pass            

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

    create_schedule_memo_users_table()
    create_schedule_favorite_performers_table()

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
            streaming_available,
            flyer_thumbnail_key,
            flyer_image_key,
            organizer_sns_url
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
    
    favorite_performers = set()

    memo_user_id = session.get("memo_user_id")

    if memo_user_id:
        cur.execute("""
            SELECT performer_name
            FROM schedule_favorite_performers
            WHERE user_id = %s
        """, (memo_user_id,))

        favorite_performers = {
            row[0] for row in cur.fetchall()
        }

    registered_performers = sorted(
        registered_performers,
        key=lambda name: (
            name not in favorite_performers,
            performer_sort_key(name)
        )
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
    saved_diary_event_ids = set()

    memo_user_id = session.get("memo_user_id")

    if memo_user_id:
        cur.execute("""
            SELECT event_id
            FROM oshi_diaries
            WHERE user_id = %s
              AND event_id IS NOT NULL
        """, (str(memo_user_id),))

        saved_diary_event_ids = {
            row[0] for row in cur.fetchall()
        }

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

        event_performers = set((event[7] or "").split())
        matched_favorites = event_performers & favorite_performers

        display_events.append({
            "id": event[0],
            "event_date": event[1],
            "start_time": start_time,
            "end_time": end_time,
            "location": event[4],
            "event_name": event[5],
            "genre": event[6],
            "performers": event[7],
            "has_favorite_performer": bool(matched_favorites),
            "streaming_available": event[8],
            "flyer_thumbnail_key": event[9],
            "flyer_image_key": event[10],
            "organizer_sns_url": event[11],
            "flyer_thumbnail_url": get_flyer_url(event[9]),
            "flyer_image_url": get_flyer_url(event[10]),
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

    if "schedule_csrf_token" not in session:
        session["schedule_csrf_token"] = secrets.token_urlsafe(32)

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
        favorite_performers=favorite_performers,
        saved_event_memos=saved_event_memos,
        saved_date_memos=saved_date_memos,
        saved_diary_event_ids=saved_diary_event_ids,
        today_views=today_views,
        memo_login_email=get_logged_in_memo_email(),
        show_google_link_prompt=should_show_google_link_prompt(),
        google_link_csrf_token=get_google_link_csrf_token(),
        schedule_csrf_token=session["schedule_csrf_token"]
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
@limiter.limit("5 per 5 minutes", methods=["POST"])
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
            streaming_available,
            organizer_sns_url
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
    performers = clean_performer_text(
        request.form.get("performers", "")
    ).strip()

    organizer_sns_url = request.form.get("organizer_sns_url", "").strip()

    if organizer_sns_url:
        from urllib.parse import urlsplit

        try:
            parsed_url = urlsplit(organizer_sns_url)
            valid_url = (
                parsed_url.scheme == "https"
                and bool(parsed_url.hostname)
                and not parsed_url.username
                and not parsed_url.password
                and not any(char.isspace() for char in organizer_sns_url)
                and len(organizer_sns_url) <= 500
            )
        except ValueError:
            valid_url = False

        if not valid_url:
            return "主催者SNSには有効なHTTPSのURLを入力してください（500文字以内）。", 400

    streaming_available = request.form.get("streaming_available") == "1"

    # 編集画面で選択されたフライヤー画像を取得
    flyer_file = request.files.get("flyer_image")

    # 現在の画像を削除するかどうか
    delete_flyer = request.form.get("delete_flyer") == "1"

    if len(event_name) > 40:
        return "イベント名は全角・半角問わず40文字以内で入力してください。", 400

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 現在登録されているフライヤー画像を取得
    cur.execute("""
        SELECT flyer_thumbnail_key, flyer_image_key
        FROM event_schedules
        WHERE id = %s
        FOR UPDATE
    """, (event_id,))

    existing_flyer = cur.fetchone()

    if existing_flyer is None:
        cur.close()
        conn.close()
        return "イベントが見つかりません。", 404
        
    old_thumbnail_key = existing_flyer[0]
    old_image_key = existing_flyer[1]

    # 初期状態では現在の画像を維持
    new_thumbnail_key = old_thumbnail_key
    new_image_key = old_image_key

    # 削除が指定された場合は画像キーを空にする
    if delete_flyer:
        new_thumbnail_key = None
        new_image_key = None

    # 削除指定がない場合だけ新しい画像をアップロード
    elif flyer_file and flyer_file.filename:
    
        try:
            new_thumbnail_key, new_image_key = upload_flyer_to_r2(
                flyer_file
            )
        except ValueError as e:
            conn.rollback()
            cur.close()
            conn.close()
            return str(e), 400
        except Exception:
            conn.rollback()
            cur.close()
            conn.close()
            raise

    try:
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
                organizer_sns_url = %s,
                streaming_available = %s,
                flyer_thumbnail_key = %s,
                flyer_image_key = %s,
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
            organizer_sns_url,
            streaming_available,
            new_thumbnail_key,
            new_image_key,
            event_id
        ))

        conn.commit()

    except Exception:
        conn.rollback()

        # 新しい画像をアップロードしていた場合は削除
        # 既存画像の削除指定では実行しない
        if (
            not delete_flyer
            and (
                new_thumbnail_key != old_thumbnail_key
                or new_image_key != old_image_key
            )
        ):
            try:
                delete_flyer_from_r2(
                    new_thumbnail_key,
                    new_image_key
                )
            except Exception:
                pass

        raise

    finally:
        cur.close()
        conn.close()

    # 画像を差し替えた場合、古い画像をR2から削除
    if (
        new_thumbnail_key != old_thumbnail_key
        or new_image_key != old_image_key
    ):
        try:
            delete_flyer_from_r2(
                old_thumbnail_key,
                old_image_key
            )
        except Exception:
            # DB更新は成功しているため、編集処理は継続
            pass
    
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
        SELECT event_date, flyer_thumbnail_key, flyer_image_key
        FROM event_schedules
        WHERE id = %s
        FOR UPDATE
    """, (event_id,))

    event = cur.fetchone()

    if event is None:
        cur.close()
        conn.close()
        return "イベントが見つかりません。", 404
    
    event_date = event[0]
    flyer_thumbnail_key = event[1]
    flyer_image_key = event[2]

    try:
        cur.execute("""
            DELETE FROM event_schedules
            WHERE id = %s
        """, (event_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    # DBからイベントを削除できた場合だけ、R2の画像も削除
    if flyer_thumbnail_key or flyer_image_key:
        try:
            delete_flyer_from_r2(
                flyer_thumbnail_key,
                flyer_image_key
            )
        except Exception:
            # R2の削除に失敗しても、イベント削除は完了させる
            pass
    
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


@event_schedule_bp.route("/schedule/admin/backup", methods=["POST"])
@admin_required

def schedule_admin_backup():
    import threading
    from flask import send_file, current_app

    # CSRFトークンを検証
    submitted_token = request.form.get("csrf_token", "")
    expected_token = session.get("admin_backup_csrf_token", "")

    if (
        not submitted_token
        or not expected_token
        or not secrets.compare_digest(submitted_token, expected_token)
    ):
        return "不正なリクエストです。", 403

    # pg_dump が実行できるか確認
    pg_dump_path = shutil.which("pg_dump")

    if not pg_dump_path:
        return "サーバーにpg_dumpがインストールされていません。", 500

    if not DATABASE_URL:
        return "データベース接続情報がありません。", 500

    # 一時ファイルを作成
    temp_file = tempfile.NamedTemporaryFile(
        suffix=".dump",
        delete=False
    )
    temp_path = temp_file.name
    temp_file.close()

    try:
        # バックアップを一時ファイルに直接保存
        subprocess.run(
            [
                pg_dump_path,
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--file=" + temp_path,
                "--dbname=" + DATABASE_URL
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=180,
            check=True
        )

        if os.path.getsize(temp_path) == 0:
            return "バックアップデータが空です。", 500

        filename = (
            "render_backup_"
            + datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y%m%d_%H%M%S")
            + ".dump"
        )

        # ダウンロード用にファイルを開く
        download_file = open(temp_path, "rb")

        def generate():
            try:
                while True:
                    chunk = download_file.read(1024 * 1024)

                    if not chunk:
                        break

                    yield chunk
            finally:
                download_file.close()
                try:
                    os.remove(temp_path)
                except OSError:
                    current_app_logger.warning(
                        "バックアップ一時ファイルの削除に失敗: %s",
                        temp_path
                    )

        from flask import Response, stream_with_context

        current_app_logger = current_app.logger

        response = Response(
            stream_with_context(generate()),
            mimetype="application/octet-stream",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                ),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff"
            }
        )

        response.content_length = os.path.getsize(temp_path)
        return response

    except subprocess.TimeoutExpired:
        return "バックアップ処理がタイムアウトしました。", 500

    except subprocess.CalledProcessError:
        current_app.logger.exception(
            "PostgreSQLバックアップに失敗しました"
        )
        return "バックアップに失敗しました。", 500

    except Exception:
        current_app.logger.exception(
            "バックアップ処理中にエラーが発生しました"
        )
        return "バックアップ処理中にエラーが発生しました。", 500

    finally:
        # エラーなどで送信が始まらなかった場合だけ削除
        if "download_file" not in locals():
            try:
                os.remove(temp_path)
            except OSError:
                pass

@event_schedule_bp.route(
    "/schedule/performer-favorite",
    methods=["POST"]
)
def schedule_performer_favorite():
    user_id = session.get("memo_user_id")

    if not user_id:
        return {"error": "ログインが必要です"}, 401

    csrf_token = request.headers.get("X-CSRF-Token", "")
    expected_token = session.get("schedule_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return {"error": "不正なリクエストです"}, 403
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "不正なリクエストです"}, 400

    performer_name = data.get("performer_name")
    favorite = data.get("favorite")

    if (
        not isinstance(performer_name, str)
        or not performer_name.strip()
        or len(performer_name) > 200
        or type(favorite) is not bool
    ):
        return {"error": "入力値が正しくありません"}, 400

    performer_name = performer_name.strip()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        if favorite:
            cur.execute("""
                INSERT INTO schedule_favorite_performers (
                    user_id, performer_name
                )
                VALUES (%s, %s)
                ON CONFLICT (user_id, performer_name)
                DO NOTHING
            """, (user_id, performer_name))
        else:
            cur.execute("""
                DELETE FROM schedule_favorite_performers
                WHERE user_id = %s
                  AND performer_name = %s
            """, (user_id, performer_name))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    return {"success": True, "favorite": favorite}


@event_schedule_bp.route(
    "/schedule/performer-favorites/save",
    methods=["POST"]
)
def schedule_performer_favorites_save():

    user_id = session.get("memo_user_id")

    if not user_id:
        return {"error": "ログインが必要です"}, 401

    csrf_token = request.headers.get("X-CSRF-Token", "")
    expected_token = session.get("schedule_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return {"error": "不正なリクエストです"}, 403

    data = request.get_json(silent=True)


    if not isinstance(data, dict):
        return {"error": "不正なリクエストです"}, 400

    performers = data.get("performers")

    if (
        not isinstance(performers, list)
        or len(performers) > 5000
        or any(
            not isinstance(name, str)
            or not name.strip()
            or len(name) > 200
            for name in performers
        )
    ):
        return {"error": "入力値が正しくありません"}, 400

    performers = list(dict.fromkeys(
        name.strip() for name in performers
    ))

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # 同じユーザーの同時保存を直列化
        cur.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            (739201, int(user_id))
        )

        cur.execute("""
            DELETE FROM schedule_favorite_performers
            WHERE user_id = %s
        """, (user_id,))

        for performer_name in performers:
            cur.execute("""
                INSERT INTO schedule_favorite_performers (
                    user_id,
                    performer_name
                )
                VALUES (%s, %s)
            """, (user_id, performer_name))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    return {
        "success": True,
        "count": len(performers)
    }


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

    
    # 出演者ステータスの検索条件
    selected_genre = request.args.get("genre", "").strip()
    sort_by = request.args.get("sort", "clicks")
    sort_order = request.args.get("order", "desc")
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 50

    if sort_by not in ("clicks", "favorites"):
        sort_by = "clicks"

    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    cur.execute("""
        WITH performer_genres AS (
            SELECT
                performer_name,
                ARRAY_AGG(DISTINCT genre ORDER BY genre)
                    FILTER (WHERE genre IS NOT NULL AND genre <> '')
                    AS genres
            FROM (
                SELECT
                    REGEXP_SPLIT_TO_TABLE(
                        TRIM(performers),
                        '\\s+'
                    ) AS performer_name,
                    genre
                FROM event_schedules
                WHERE performers IS NOT NULL
                  AND TRIM(performers) <> ''
            ) AS names
            WHERE performer_name <> ''
            GROUP BY performer_name
        ),
        clicks AS (
            SELECT
                performer_name,
                SUM(click_count) AS click_count
            FROM schedule_performer_clicks
            GROUP BY performer_name
        ),
        favorites AS (
            SELECT
                performer_name,
                COUNT(*) AS favorite_count
            FROM schedule_favorite_performers
            GROUP BY performer_name
        ),
        all_performers AS (
            SELECT performer_name FROM performer_genres
            UNION
            SELECT performer_name FROM clicks
            UNION
            SELECT performer_name FROM favorites
        )
        SELECT
            p.performer_name,
            COALESCE(g.genres, ARRAY[]::TEXT[]),
            COALESCE(c.click_count, 0),
            COALESCE(f.favorite_count, 0)
        FROM all_performers p
        LEFT JOIN performer_genres g
            ON p.performer_name = g.performer_name
        LEFT JOIN clicks c
            ON p.performer_name = c.performer_name
        LEFT JOIN favorites f
            ON p.performer_name = f.performer_name
    """)

    performer_status = []

    for name, genres, clicks, favorites in cur.fetchall():

        if selected_genre and selected_genre not in genres:
            continue

        performer_status.append({
            "name": name,
            "genres": genres,
            "clicks": clicks,
            "favorites": favorites
        })

    # 同数の場合は名前順で安定させる
    performer_status.sort(
        key=lambda p: performer_sort_key(p["name"])
    )

    sort_key = (
        "favorites" if sort_by == "favorites"
        else "clicks"
    )

    performer_status.sort(
        key=lambda p: p[sort_key],
        reverse=(sort_order == "desc")
    )

    total_performers = len(performer_status)
    total_pages = max(
        1,
        (total_performers + per_page - 1) // per_page
    )

    page = min(page, total_pages)

    start_index = (page - 1) * per_page

    performer_status = performer_status[
        start_index:start_index + per_page
    ]

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

    # ユーザー登録状況
    cur.execute("""
        SELECT
            COUNT(*),
            COUNT(*) FILTER (
                WHERE (created_at AT TIME ZONE 'Asia/Tokyo')::date =
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo')::date
            ),
            COUNT(*) FILTER (
                WHERE DATE_TRUNC(
                    'month',
                    created_at AT TIME ZONE 'Asia/Tokyo'
                ) = DATE_TRUNC(
                    'month',
                    CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo'
                )
            )
        FROM schedule_memo_users
    """)

    registered_users, today_registrations, month_registrations = cur.fetchone()

    # リピート率（今月・累計）
    cur.execute("""
        WITH visitor_counts AS (
            SELECT
                visitor_id,
                COUNT(*) AS total_days,
                COUNT(*) FILTER (
                    WHERE visit_date >= DATE_TRUNC(
                        'month',
                        CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Tokyo'
                    )::date
                ) AS month_days
            FROM schedule_unique_visitors
            GROUP BY visitor_id
        )
        SELECT
            COALESCE(
                ROUND(
                    COUNT(*) FILTER (WHERE month_days >= 2) * 100.0
                    / NULLIF(COUNT(*) FILTER (WHERE month_days >= 1), 0),
                    1
                ),
                0
            ),
            COALESCE(
                ROUND(
                    COUNT(*) FILTER (WHERE total_days >= 2) * 100.0
                    / NULLIF(COUNT(*), 0),
                    1
                ),
                0
            )
        FROM visitor_counts
    """)

    month_repeat_rate, total_repeat_rate = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "schedule_stats.html",
        today_views=today_views,
        month_views=month_views,
        total_views=total_views,
        performer_status=performer_status,
        selected_genre=selected_genre,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_performers=total_performers,
        daily_views=daily_views,
        device_views=device_views,
        today_unique=today_unique,
        month_unique=month_unique,
        total_unique=total_unique,
        registered_users=registered_users,
        today_registrations=today_registrations,
        month_registrations=month_registrations,
        month_repeat_rate=month_repeat_rate,
        total_repeat_rate=total_repeat_rate
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
            organizer_sns_url
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

    csrf_token = request.headers.get("X-CSRF-Token", "")
    expected_token = session.get("schedule_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return {"error": "不正なリクエストです"}, 403

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

    csrf_token = request.headers.get("X-CSRF-Token", "")
    expected_token = session.get("schedule_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return {"error": "不正なリクエストです"}, 403

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

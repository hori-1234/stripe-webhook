import os
import psycopg2

from flask import Blueprint, session
from event_schedule.memo_auth import is_memo_logged_in

oshikatsu_bp = Blueprint(
    "oshikatsu",
    __name__,
    url_prefix="/oshikatsu"
)


@oshikatsu_bp.route("/")
def oshikatsu_home():
    import secrets
    from oshikatsu.nikki import render_nikki_form

    logged_in = is_memo_logged_in()

    if logged_in and not session.get("oshi_csrf_token"):
        session["oshi_csrf_token"] = secrets.token_urlsafe(32)

    return render_nikki_form(
        logged_in=logged_in,
        csrf_token=session.get("oshi_csrf_token", "")
    )


@oshikatsu_bp.route("/save", methods=["POST"])
def save_oshi_diary():
    import secrets
    from datetime import date
    from flask import request

    if not is_memo_logged_in():
        return "ログインが必要です", 401

    csrf_token = request.form.get("csrf_token", "")
    expected_token = session.get("oshi_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return "不正なリクエストです", 403

    user_id = session.get("memo_user_id")

    photos = request.files.getlist("photos")

    if len(photos) > 10:
        return "写真は最大10枚までです", 400

    try:
        event_date = date.fromisoformat(
            request.form.get("event_date", "")
        )
    
    except ValueError:
        return "日付が正しくありません", 400

    event_name = request.form.get("event_name", "").strip()
    place = request.form.get("place", "").strip()
    performers = request.form.get("performers", "").strip()
    diary_text = request.form.get("diary_text", "").strip()

    if (
        len(event_name) > 500
        or len(place) > 500
        or len(performers) > 5000
        or len(diary_text) > 50000
    ):
        return "入力文字数が上限を超えています", 400

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO oshi_diaries (
                        user_id,
                        event_date,
                        event_name,
                        place,
                        performers,
                        diary_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    str(user_id),
                    event_date,
                    event_name,
                    place,
                    performers,
                    diary_text
                ))

                diary_id = cur.fetchone()[0]
                
                from oshikatsu.oshi_photo_save import save_oshi_photos

                save_oshi_photos(
                    conn=conn,
                    photos=photos,
                    user_id=user_id,
                    diary_id=diary_id
                )
    
    finally:
        conn.close()

    return f"推し活日記を保存しました（ID：{diary_id}）"


@oshikatsu_bp.route("/view/<int:diary_id>", methods=["GET"])
def view_oshi_diary(diary_id):
    if not is_memo_logged_in():
        return "ログインが必要です", 401

    user_id = session.get("memo_user_id")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    event_date,
                    event_name,
                    place,
                    performers,
                    diary_text
                FROM oshi_diaries
                WHERE id = %s
                  AND user_id = %s
            """, (diary_id, str(user_id)))

            diary = cur.fetchone()
    finally:
        conn.close()

    if diary is None:
        return "日記が見つかりません", 404

    from oshikatsu.nikki import render_nikki_view
    from oshikatsu.nikki_photo_view import render_nikki_photo_view

    photo_view = render_nikki_photo_view(
        diary_id=diary_id,
        user_id=user_id
    )

    return render_nikki_view(
        diary,
        photo_view=photo_view,
        diary_id=diary_id
    )


@oshikatsu_bp.route("/edit/<int:diary_id>", methods=["GET"])
def edit_oshi_diary(diary_id):
    import secrets

    if not is_memo_logged_in():
        return "ログインが必要です", 401

    user_id = session.get("memo_user_id")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    event_date,
                    event_name,
                    place,
                    performers,
                    diary_text
                FROM oshi_diaries
                WHERE id = %s
                  AND user_id = %s
            """, (
                diary_id,
                str(user_id)
            ))

            diary = cur.fetchone()

    finally:
        conn.close()

    if diary is None:
        return "日記が見つかりません", 404

    if not session.get("oshi_csrf_token"):
        session["oshi_csrf_token"] = secrets.token_urlsafe(32)

    from oshikatsu.nikki_edit import render_nikki_edit
    from oshikatsu.oshi_photo_list import get_oshi_edit_photos

    saved_photos = get_oshi_edit_photos(
        diary_id=diary_id,
        user_id=user_id
    )

    return render_nikki_edit(
        diary=diary,
        diary_id=diary_id,
        csrf_token=session["oshi_csrf_token"],
        saved_photos=saved_photos
    )


@oshikatsu_bp.route("/update/<int:diary_id>", methods=["POST"])
def update_oshi_diary_route(diary_id):
    import secrets
    from flask import request, redirect, url_for
    from oshikatsu.oshi_diary_update import update_oshi_diary

    if not is_memo_logged_in():
        return "ログインが必要です", 401

    csrf_token = request.form.get("csrf_token", "")
    expected_token = session.get("oshi_csrf_token", "")

    if (
        not csrf_token
        or not expected_token
        or not secrets.compare_digest(csrf_token, expected_token)
    ):
        return "不正なリクエストです", 403

    user_id = session.get("memo_user_id")

    from oshikatsu.oshi_photo_update import validate_oshi_photo_update

    try:
        order_data, removed_ids, new_photos = validate_oshi_photo_update(
            form=request.form,
            photos=request.files.getlist("photos")
        )
    except ValueError as e:
        return str(e), 400

        from oshikatsu.oshi_photo_update import apply_oshi_photo_update

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn:
            success, message = update_oshi_diary(
                diary_id=diary_id,
                user_id=user_id,
                form=request.form,
                conn=conn
            )

            if not success:
                raise ValueError(message)

            apply_oshi_photo_update(
                diary_id=diary_id,
                user_id=user_id,
                order_data=order_data,
                removed_ids=removed_ids,
                new_photos=new_photos,
                conn=conn
            )

    except ValueError as e:
        message = str(e)

        if message == "日記が見つかりません":
            return message, 404

        return message, 400

    except Exception:
        import logging
        logging.exception("推し活日記の更新に失敗しました")
        return "日記の更新に失敗しました", 500

    finally:
        conn.close()

    return redirect(
        url_for(
            "oshikatsu.view_oshi_diary",
            diary_id=diary_id
        )
    )

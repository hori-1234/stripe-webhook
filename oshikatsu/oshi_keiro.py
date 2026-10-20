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

    from flask import redirect, url_for

    response = redirect(
        url_for("oshikatsu.list_oshi_diaries")
    )

    response.set_cookie(
        "oshi_save_success",
        "1",
        max_age=60,
        httponly=False,
        samesite="Lax"
    )

    return response


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

            prev_diary_id = None
            next_diary_id = None

            if diary is not None:

                cur.execute("""
                    SELECT id
                    FROM oshi_diaries
                    WHERE user_id = %s
                      AND (
                          event_date < %s
                          OR (event_date = %s AND id < %s)
                      )
                    ORDER BY event_date DESC, id DESC
                    LIMIT 1
                """, (
                    str(user_id),
                    diary[0],
                    diary[0],
                    diary_id
                ))

                row = cur.fetchone()
                if row:
                    prev_diary_id = row[0]

                cur.execute("""
                    SELECT id
                    FROM oshi_diaries
                    WHERE user_id = %s
                      AND (
                          event_date > %s
                          OR (event_date = %s AND id > %s)
                      )
                    ORDER BY event_date ASC, id ASC
                    LIMIT 1
                """, (
                    str(user_id),
                    diary[0],
                    diary[0],
                    diary_id
                ))

                row = cur.fetchone()
                if row:
                    next_diary_id = row[0]

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
        diary_id=diary_id,
        prev_diary_id=prev_diary_id,
        next_diary_id=next_diary_id
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

@oshikatsu_bp.route("/list", methods=["GET"])
def list_oshi_diaries():
    from flask import request
    from oshikatsu.nikki_list import render_nikki_list

    if not is_memo_logged_in():
        return """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ログイン確認</title>
            <style>
                body {
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(0, 0, 0, 0.35);
                    font-family: sans-serif;
                }

                .login-dialog {
                    width: 280px;
                    max-width: calc(100% - 40px);
                    padding: 25px;
                    box-sizing: border-box;
                    background: white;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                }

                .login-dialog p {
                    margin: 15px 0 25px;
                }

                .login-dialog-buttons {
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                }

                .login-dialog-buttons a {
                    padding: 10px 25px;
                    border: 1px solid #888;
                    border-radius: 6px;
                    background: #f5f5f5;
                    color: #222;
                    text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="login-dialog">
                <p>ログインが必要です</p>
                <div class="login-dialog-buttons">
                    <a href="/schedule/login">OK</a>
                    <a href="/schedule">戻る</a>
                </div>
            </div>
        </body>
        </html>
        """

    user_id = session.get("memo_user_id")

    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    performer = request.args.get("performer", "").strip()
    keyword = request.args.get("keyword", "").strip()

    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    per_page = 10

    conditions = ["d.user_id = %s"]
    params = [str(user_id)]

    if start_date:
        conditions.append("d.event_date >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("d.event_date <= %s")
        params.append(end_date)

    if performer:
        conditions.append("d.performers ILIKE %s")
        params.append(f"%{performer}%")

    if keyword:
        conditions.append("""
            (
                d.event_name ILIKE %s
                OR d.place ILIKE %s
                OR d.performers ILIKE %s
                OR d.diary_text ILIKE %s
            )
        """)
        params.extend([f"%{keyword}%"] * 4)

    where_sql = " AND ".join(conditions)

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*)
                FROM oshi_diaries AS d
                WHERE {where_sql}
            """, params)

            total_count = cur.fetchone()[0]
            total_pages = max(1, (total_count + per_page - 1) // per_page)
            page = min(page, total_pages)

            cur.execute(f"""
                SELECT
                    d.id,
                    d.event_date,
                    d.event_name,
                    d.performers,
                    (
                        SELECT p.id
                        FROM oshi_diary_photos AS p
                        WHERE p.diary_id = d.id
                        ORDER BY p.photo_order, p.id
                        LIMIT 1
                    ) AS thumbnail_id
                FROM oshi_diaries AS d
                WHERE {where_sql}
                ORDER BY d.event_date DESC, d.id DESC
                LIMIT %s OFFSET %s
            """, params + [per_page, (page - 1) * per_page])

            diaries = cur.fetchall()

    finally:
        conn.close()

    return render_nikki_list(
        diaries=diaries,
        start_date=start_date,
        end_date=end_date,
        performer=performer,
        keyword=keyword,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )

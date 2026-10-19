import os
import psycopg2

from io import BytesIO

from flask import (
    Blueprint,
    session,
    send_file,
    abort
)

from event_schedule.memo_auth import is_memo_logged_in
from oshikatsu.oshi_r2 import get_oshi_photo


oshi_photo_bp = Blueprint(
    "oshi_photo",
    __name__,
    url_prefix="/oshikatsu"
)


@oshi_photo_bp.route("/photo/<int:photo_id>")
def view_oshi_photo(photo_id):

    if not is_memo_logged_in():
        abort(401)

    user_id = session.get("memo_user_id")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.r2_key
                FROM oshi_diary_photos AS p
                JOIN oshi_diaries AS d
                  ON d.id = p.diary_id
                WHERE p.id = %s
                  AND d.user_id = %s
            """, (
                photo_id,
                str(user_id)
            ))

            row = cur.fetchone()

    finally:
        conn.close()

    if row is None:
        abort(404)

    r2_key = row[0]

    image_bytes = get_oshi_photo(r2_key)

    if hasattr(image_bytes, "read"):
        image_bytes = image_bytes.read()

    return send_file(
        BytesIO(image_bytes),
        mimetype="image/webp",
        as_attachment=False
    )

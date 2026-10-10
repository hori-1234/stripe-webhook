import os
import psycopg2
from datetime import datetime
from zoneinfo import ZoneInfo

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_pending_alarms():
    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                id,
                recipient_email,
                subject,
                body
            FROM schedule_memo_alarms
            WHERE status = 'pending'
              AND scheduled_at <= %s
            ORDER BY scheduled_at, id
        """, (now_jst,))

        return cur.fetchall()

    finally:
        cur.close()
        conn.close()

  def send_alarm_email(recipient_email, subject, body):
    import resend

    resend.api_key = os.environ.get("RESEND_API_KEY")

    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEYが設定されていません")

    response = resend.Emails.send({
        "from": os.environ["ALARM_FROM_EMAIL"],
        "to": [recipient_email],
        "subject": subject,
        "text": body
    })

    return response


def process_pending_alarms():
    alarms = get_pending_alarms()

    for alarm_id, recipient_email, subject, body in alarms:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        try:
            # 送信前に処理対象を確保する
            cur.execute("""
                UPDATE schedule_memo_alarms
                SET status = 'processing',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'pending'
                RETURNING id
            """, (alarm_id,))

            if cur.fetchone() is None:
                conn.rollback()
                continue

            conn.commit()

            # メール送信
            send_alarm_email(recipient_email, subject, body)

            # 送信成功
            cur.execute("""
                UPDATE schedule_memo_alarms
                SET status = 'sent',
                    sent_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'processing'
            """, (alarm_id,))

            conn.commit()
            print(f"アラーム送信成功: ID={alarm_id}")

        except Exception as error:
            conn.rollback()

            cur.execute("""
                UPDATE schedule_memo_alarms
                SET status = 'failed',
                    attempt_count = attempt_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'processing'
            """, (alarm_id,))

            conn.commit()
            print(f"アラーム送信失敗: ID={alarm_id}, error={error}")

        finally:
            cur.close()
            conn.close()

if __name__ == "__main__":
  process_pending_alarms()

import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]


def send_syuwa_approval_email(email, applicant_name, password_url):

    text = f"""{applicant_name} 様

手話アプリへの登録申請が承認されました。

以下のURLからパスワードを設定してください。

{password_url}

【注意事項】
・URLの有効期限は発行から7日間です。
・URLは一度使用すると無効になります。
・このURLを第三者に共有しないでください。

パスワードの設定が完了すると、
動画登録用アカウントの準備が整います。

よろしくお願いいたします。

運営
"""

    response = resend.Emails.send({
        "from": "shop@nwoshi.com",
        "to": [email],
        "subject": "手話アプリ｜登録申請が承認されました",
        "text": text
    })

    return response


def send_syuwa_password_reset_email(email, applicant_name, password_url):

    text = f"""{applicant_name} 様

手話アプリのパスワード再設定URLを発行しました。

以下のURLから新しいパスワードを設定してください。

{password_url}

【注意事項】
・URLの有効期限は発行から1時間です。
・URLは一度使用すると無効になります。
・このURLを第三者に共有しないでください。
・パスワードは6桁の半角英数字で設定してください。

このメールに心当たりがない場合は、
URLを開かずに破棄してください。

よろしくお願いいたします。

運営
"""

    response = resend.Emails.send({
        "from": "shop@nwoshi.com",
        "to": [email],
        "subject": "手話アプリ｜パスワード再設定のご案内",
        "text": text
    })

    return response

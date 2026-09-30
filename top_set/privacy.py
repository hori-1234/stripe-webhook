from flask import Blueprint, render_template_string

privacy_bp = Blueprint("privacy", __name__)


@privacy_bp.route("/privacy")
def privacy():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>プライバシーポリシー</title>
</head>

<body>

    <h1>プライバシーポリシー</h1>

    <h2>個人情報の取得について</h2>

    <p>
    当方は、商品の購入、チケットの発行、お問い合わせ等に必要な範囲で、氏名、メールアドレスその他の個人情報を取得する場合があります。
    </p>

    <h2>個人情報の利用目的</h2>

    <p>
    取得した個人情報は、商品の販売・発送、チケットの発行、PDF商品の提供、購入者への連絡、お問い合わせへの対応、その他サービスの提供に必要な範囲で利用します。
    </p>

    <h2>個人情報の第三者提供について</h2>

    <p>
    法令に基づく場合を除き、本人の同意なく個人情報を第三者に提供することはありません。
    </p>

    <h2>個人情報の管理について</h2>

    <p>
    取得した個人情報について、不正アクセス、紛失、漏えい等を防止するため、適切な安全管理に努めます。
    </p>

    <h2>個人情報の開示・訂正・削除について</h2>

    <p>
    本人から個人情報の開示、訂正、削除等の請求があった場合は、本人確認を行った上で、法令に従い適切に対応します。
    </p>

    <h2>外部サービスの利用について</h2>

    <p>
    当サイトでは、決済、メール送信、データ保存等のため、外部サービスを利用する場合があります。
    </p>

    <h2>プライバシーポリシーの変更について</h2>

    <p>
    本プライバシーポリシーの内容は、必要に応じて変更する場合があります。
    </p>

    <h2>お問い合わせ窓口</h2>

    <p>
    個人情報の取扱いに関するお問い合わせは、下記メールアドレスまでお願いいたします。
    </p>

    <p>
    <a href="mailto:shop@nwoshi.com">shop@nwoshi.com</a>
    </p>


</body>
</html>
""")

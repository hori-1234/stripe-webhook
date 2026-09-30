from flask import Blueprint, render_template_string

contact_bp = Blueprint("contact", __name__)


@contact_bp.route("/contact")
def contact():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>お問い合わせ</title>
</head>

<body>

    <h1>お問い合わせ</h1>

    <p>
        商品・チケット・キャンセル・返品等に関するお問い合わせは、
        下記メールアドレスまでお願いいたします。
    </p>

    <p>
        <a href="mailto:shop@nwoshi.com">shop@nwoshi.com</a>
    </p>

</body>
</html>
""")

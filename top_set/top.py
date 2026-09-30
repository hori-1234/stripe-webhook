from flask import Blueprint, render_template_string

top_bp = Blueprint("top", __name__)

@top_bp.route("/")
def top():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>マイマケ</title>
</head>

<body>

    <h1>マイマケ</h1>

    <p>
        <a href="/cancel-policy">
            キャンセル・返品・払い戻しについて
        </a>
    </p>

    <p>
        <a href="/contact">
            お問い合わせ
        </a>
    </p>

    <p>
        <a href="/privacy">
            プライバシーポリシー
        </a>
    </p>

    <footer>
        <a href="/tokushoho">特定商取引法に基づく表記</a>
    </footer>

</body>
</html>
""")

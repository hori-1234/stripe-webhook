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

    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, "Noto Sans JP", sans-serif;
            background-color: #f7f7f7;
            color: #333;
            text-align: center;
        }

        h1 {
            margin-top: 60px;
            font-size: 36px;
        }
        .menu {
            width: 90%;
            max-width: 500px;
            margin: 40px auto;
        }

        .menu p {
            margin: 15px 0;
        }
        
        .menu a {
            display: block;
            padding: 15px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            color: #333;
            text-decoration: none;
        }

        footer {
            margin-top: 80px;
            padding: 20px;
            font-size: 14px;
        }

        footer a {
            color: #666;
            text-decoration: none;
        }

        .menu a:hover {
            background-color: #eeeeee;
        }


    </style>
</head>

<body>

    <h1>マイマケ</h1>
    <div class="menu">
    
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

    </div>

    <footer>
        <a href="/tokushoho">特定商取引法に基づく表記</a>
    </footer>

</body>
</html>
""")

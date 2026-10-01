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
    <title>W's</title>

    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, "Noto Sans JP", sans-serif;
            background-color: #f7f7f7;
            color: #333;
            text-align: center;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        h1 {
            margin-top: 60px;
            margin-left: 30px;
            font-size: 36px;
            text-align: left;
        }
        .menu {
            width: 90%;
            max-width: 500px;
            margin: 40px 0 40px 30px;
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
            margin-top: auto;
            padding: 20px 30px;
            font-size: 14px;
            text-align: left;
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

    <h1>W's</h1>
    <div class="menu">

    <p>
        <a href="/member-video">
            クリサポ限定動画検索
        </a>
    </p>
    
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

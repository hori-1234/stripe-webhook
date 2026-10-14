
from flask import Blueprint, render_template_string

purpose_bp = Blueprint("purpose", __name__)


@purpose_bp.route("/purpose")
def purpose():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>目的 | イベスケ</title>

    <style>
        body {
            margin: 0;
            padding: 25px 15px;
            background: #ffffff;
            color: #222;
            font-family: sans-serif;
            line-height: 1.8;
        }

        .purpose-container {
            max-width: 1000px;
            margin: 0 auto;
            text-align: center;
        }

        h1 {
            font-size: 28px;
            margin: 10px 0 30px;
        }

        .purpose-section {
            margin-bottom: 2em;
        }

        .purpose-section h2 {
            margin: 0;
            padding: 12px 15px;
            background: linear-gradient(to top, #0879d7, #279ed0);
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            border-radius: 4px 4px 0 0;
        }

        .purpose-section p {
            margin: 0;
            padding: 18px 15px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
        }

        .purpose-highlight {
            font-weight: bold;
            font-size: 19px;
        }

        @media (max-width: 700px) {
            body {
                padding: 15px 10px;
            }

            h1 {
                font-size: 22px;
            }

            .purpose-section h2 {
                font-size: 16px;
                padding: 10px 12px;
            }

            .purpose-section p {
                padding: 15px 12px;
                font-size: 14px;
            }

            .purpose-highlight {
                font-size: 16px;
            }
        }
    </style>
</head>

<body>

<div class="purpose-container">

    <h1>目的</h1>

    <section class="purpose-section">
        <h2>イベスケについて</h2>

        <p>
            イベスケは、個人で開発・運営しているイベント情報サイトです。
        </p>

        <p class="purpose-highlight">
            推しとの一期一会を、見逃さないために。
        </p>

        <p>
            イベスケは、大切な「推し」の活動やイベント情報を、
            ひと目で確認できるスケジュールサイトです。
            日々の仕事や生活に追われ、
            気になるイベントや出演情報を
            すべて把握するのは簡単ではありません。
        </p>

        <p>
            だからこそ、限られた時間の中でも、
            大切な「推し」と出会える機会を見逃してほしくない。
            そんな想いから、イベスケは生まれました。
        </p>
    </section>

    <section class="purpose-section">
        <h2>演者様・イベント主催者様へ</h2>

        <p>
            また、ファンの方だけでなく、
            演者様やイベント主催者様にも
            便利に活用していただけるサイトを目指しています。
        </p>

        <p>
            ライブやイベントの出演予定はもちろん、
            撮影日などの活動スケジュールも、
            メモや付箋を貼るような感覚で整理し、
            カレンダー上でわかりやすく確認できる仕組みを提供しています。
        </p>
    </section>

    <section class="purpose-section">
        <h2>イベスケが目指すもの</h2>

        <p class="purpose-highlight">
            ファンには、推しと出会うきっかけを。
        </p>

        <p class="purpose-highlight">
            演者様には、活動を整理し、
            ファンに知ってもらう機会を。
        </p>

        <p>
            イベスケは、そんな双方の活動を
            サポートするサイトを目指しています。
        </p>
    </section>

    <section class="purpose-section">
        <h2>ご利用について</h2>

        <p>
            なお、イベスケは無料でご利用いただけます。
        </p>
    </section>

</div>

</body>
</html>
""")

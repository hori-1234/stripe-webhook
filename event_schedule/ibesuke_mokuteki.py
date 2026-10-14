
from flask import Blueprint, render_template_string

ibesuke_mokuteki = Blueprint("ibesuke_mokuteki", __name__)

@ibesuke_mokuteki.route("/purpose")
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
            padding: 4px 15px;
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
            イベスケは個人で開発・運営している、<br>
            イベント情報サイトです。
        </p>

        <p class="purpose-highlight">
            推しとの一期一会を、見逃さないために。
        </p>

        <p>
            イベスケは、<ber>
            大切な「推し」の活動や<br>
            イベント情報を、<br>
            ひと目で確認できる<br>
            スケジュールサイトです。<br>
            日々の仕事や生活に追われ、<br>
            気になるイベントや出演情報を<br>
            すべて把握するのは簡単ではありません。<br>
        </p>

        <p>
            だからこそ、<br>
            限られた時間の中でも、<br>
            大切な「推し」と<br>
            出会える機会を見逃してほしくない。<br>
            そんな想いから、<br>
            イベスケは生まれました。<br>
        </p>
    </section>

    <section class="purpose-section">
        <h2>活動者様へ</h2>

        <p>
            ファンの方だけでなく<br>
            演者様・活動者様にとって<br>
            便利に活用していただけるサイトを<br>
            目指しています。<br>
        </p>

        <p>
            ライブやイベントの出演予定はもちろん、<br>
            撮影日などの活動スケジュールも、<br>
            メモや付箋を貼るような感覚で整理し、<br>
            カレンダー上で<br>
            わかりやすく確認できる仕組みを<br>
            提供しています。<br>
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
            イベスケは無料でご利用いただけます。
        </p>
    </section>

</div>

</body>
</html>
""")

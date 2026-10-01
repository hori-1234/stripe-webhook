from flask import Blueprint, render_template_string, request
from admin_auth import member_required

kuri_move_sarch_bp = Blueprint("kuri_move_sarch", __name__)


@kuri_move_sarch_bp.route("/member-video")
@member_required
def member_video():
    performer = request.args.get("performer", "").strip()

    videos = []

    results = []

    if performer:
        for video in videos:
            if performer.lower() in video["performers"].lower():
                results.append(video)
  
    return render_template_string("""
    
<!DOCTYPE html>
<html lang="ja">
<head>
    <style>
        input[type="text"] {
            width: 300px;
            padding: 12px;
            font-size: 18px;
        }

        button {
            padding: 12px 24px;
            font-size: 18px;
        }
    </style>

    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>動画検索</title>
</head>

<body>

    <h1>動画検索</h1>

    <form method="GET" action="/member-video">
    <input
        type="text"
        name="performer"
        placeholder="出演者名を入力"
    >

    <button type="submit">
        検索
    </button>
    
</form>

<hr>

<h2>検索結果</h2>

{% if performer %}
    <p>「{{ performer }}」の動画</p>
{% endif %}

{% for video in results %}
    <p>
        <a href="{{ video['url'] }}" target="_blank">
            Xで動画を見る
        </a>
    </p>
{% endfor %}

{% if performer and not results %}
    <p>該当する動画はありません。</p>
{% endif %}

</body>
</html>
""", performer=performer, results=results)


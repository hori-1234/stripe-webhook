from flask import Blueprint, render_template_string, request

kuri_move_sarch_bp = Blueprint("kuri_move_sarch", __name__)


@kuri_move_sarch_bp.route("/member-video")
def member_video():
    performer = request.args.get("performer", "").strip()
  
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>会員限定動画検索</title>
</head>

<body>

    <h1>会員限定動画検索</h1>

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

{% if performer %}
    <h2>検索結果</h2>
    <p>「{{ performer }}」の動画</p>
{% endif %}

</body>
</html>
""", performer=performer)



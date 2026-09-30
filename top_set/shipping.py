from flask import Blueprint, render_template_string

shipping_bp = Blueprint("shipping", __name__)


@shipping_bp.route("/shipping")
def shipping():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>送料について</title>
</head>

<body>

    <h1>送料について</h1>

    <h2>現物商品の送料について</h2>

    <p>
    現物商品の発送には、別途送料が発生します。
    </p>

    <p>
    送料の詳細については、こちらのページでご案内します。
    </p>


</body>
</html>
""")

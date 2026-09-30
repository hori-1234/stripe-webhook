from flask import Blueprint, render_template_string

cancel_policy_bp = Blueprint("cancel_policy", __name__)


@cancel_policy_bp.route("/cancel-policy")
def cancel_policy():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>キャンセル・返品・払い戻しについて</title>
</head>

<body>

    <h1>キャンセル・返品・払い戻しについて</h1>

</body>
</html>
""")

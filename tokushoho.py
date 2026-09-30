from flask import Blueprint, render_template_string

tokushoho_bp = Blueprint("tokushoho", __name__)


@tokushoho_bp.route("/tokushoho")
def tokushoho():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>特定商取引法に基づく表記</title>
</head>

<body>

    <h1>特定商取引法に基づく表記</h1>

    <h2>販売価格</h2>

    <p>
    各商品・チケットの販売ページに表示された価格
    </p>

    <h2>商品代金以外に必要な料金</h2>

    <p>
    現物商品の送料が発生します。送料の詳細は「送料について」ページをご確認ください。
    </p>

    <h2>支払方法</h2>

    <p>
    クレジットカード決済
    </p>

    <h2>支払時期</h2>

    <p>
    購入手続き完了時に決済されます。
    </p>

    <h2>商品の提供時期</h2>

    <p>
    チケット：決済完了後、チケットをメールにて発行します。
    </p>

    <p>
    PDF商品：決済完了後、PDFファイルをメールにて提供します。
    </p>

    <p>
    現物商品：決済完了後7日以内に発送します。
    </p>

    <h2>申込み有効期限</h2>

    <p>
    現物商品：在庫がなくなり次第、販売を終了します。
    </p>

    <p>
    チケット：イベント開催日の前日まで販売します。
    </p>

    <p>
    PDF商品：販売期限はありません。
    </p>

    <h2>販売数量の制限</h2>

    <p>
    商品・チケットごとに購入数量を制限する場合があります。制限がある場合は、各販売ページに表示します。
    </p>

    <h2>動作環境</h2>

    <p>
    PDF商品の閲覧には、PDF形式のファイルを閲覧できる環境が必要です。
    </p>

    <h2>特別な販売条件</h2>

    <p>
    特にありません。
    </p>

    <h2>販売事業者・所在地・電話番号</h2>

    <p>
    請求があった場合、遅滞なく開示いたします。
    </p>

</body>
</html>
""")

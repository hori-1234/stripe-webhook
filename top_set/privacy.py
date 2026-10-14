from flask import Blueprint, render_template_string

privacy_bp = Blueprint("privacy", __name__)


@privacy_bp.route("/privacy")
def privacy():
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>プライバシーポリシー | イベスケ</title>

    <style>
        body {
            margin: 0;
            padding: 25px 15px;
            background: #ffffff;
            color: #222;
            font-family: sans-serif;
            line-height: 1.8;
        }

        .privacy-container {
            max-width: 1000px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            font-size: 28px;
            margin: 10px 0 30px;
        }

        .privacy-intro {
            padding: 12px 15px;
            margin-bottom: 30px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
        }

        .privacy-section {
            margin-bottom: 2em;
        }

        .privacy-section h2 {
            margin: 0;
            padding: 12px 15px;
            background: linear-gradient(to top, #0879d7, #279ed0);
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
            border-radius: 4px 4px 0 0;
        }

        .privacy-section p {
            margin: 0;
            padding: 12px 15px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
        }

        .privacy-section ul {
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .privacy-section li {
            margin: 0;
            padding: 10px 15px 10px 30px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.2);
            position: relative;
        }

        .privacy-section li::before {
            content: "・";
            position: absolute;
            left: 12px;
        }

        a {
            color: #0879d7;
            overflow-wrap: anywhere;
        }

        .privacy-footer {
            margin-top: 30px;
            padding: 20px 10px;
            text-align: center;
            color: #666;
            font-size: 13px;
        }

        @media (max-width: 700px) {
            body {
                padding: 15px 10px;
            }

            h1 {
                font-size: 22px;
            }

            .privacy-section h2 {
                font-size: 16px;
                padding: 10px 12px;
            }

            .privacy-section p {
                padding: 10px 12px;
                font-size: 14px;
            }

            .privacy-section li {
                padding: 10px 12px 10px 26px;
                font-size: 14px;
            }

            .privacy-section li::before {
                left: 8px;
            }
        }
    </style>
</head>

<body>

<div class="privacy-container">

    <h1>プライバシーポリシー</h1>

    <div class="privacy-intro">
        当方は、運営するウェブサイトおよびサービス
        （以下「当サイト」といいます）において、
        利用者の個人情報を適切に取り扱うため、
        以下のとおりプライバシーポリシーを定めます。
    </div>

    <section class="privacy-section">
        <h2>1. 個人情報の取得について</h2>

        <p>
            当サイトでは、以下のサービスを提供するため、
            必要な範囲で個人情報を取得する場合があります。
        </p>

        <ul>
            <li>イベント情報の登録・編集</li>
            <li>Googleアカウントまたはメールアドレスによるログイン</li>
            <li>チケットの購入・発行</li>
            <li>商品の販売・発送</li>
            <li>PDF商品の提供</li>
            <li>お問い合わせへの対応</li>
        </ul>

        <p>
            取得する情報には、氏名、メールアドレス、
            ログイン認証に必要な情報、購入情報、
            イベント登録情報などが含まれる場合があります。
        </p>

        <p>
            Googleアカウントによるログインでは、
            利用者が許可した範囲で、Googleから
            メールアドレスなどのアカウント情報を取得する場合があります。
            なお、Googleアカウントのパスワードを
            当サイトが直接取得することはありません。
        </p>
    </section>

    <section class="privacy-section">
        <h2>2. 個人情報の利用目的</h2>

        <p>取得した個人情報は、以下の目的で利用します。</p>

        <ul>
            <li>利用者の認証およびログイン機能の提供</li>
            <li>イベント情報の登録・管理</li>
            <li>お気に入り機能やマイメモ機能の提供</li>
            <li>チケットの発行および購入内容の確認</li>
            <li>商品の販売・発送およびPDF商品の提供</li>
            <li>サービスに関する連絡やメールの送信</li>
            <li>お問い合わせへの対応</li>
            <li>不正利用の防止およびセキュリティの確保</li>
            <li>サービスの改善および利用状況の把握</li>
        </ul>

        <p>
            取得した個人情報は、上記の目的に必要な範囲で取り扱います。
        </p>
    </section>

    <section class="privacy-section">
        <h2>3. イベント登録情報について</h2>

        <p>
            イベスケでは、利用者がイベント名、開催日時、
            開催場所、出演者名、フライヤー画像などの情報を登録できます。
        </p>

        <p>
            登録されたイベント情報は、
            他の利用者が閲覧できる状態で公開される場合があります。
        </p>

        <p>
            利用者は、第三者の個人情報を登録する場合、
            必要な権限や同意を得るなど、
            適切に取り扱うものとします。
        </p>

        <p>
            ログイン用メールアドレスや個人用メモなど、
            公開を目的としていない情報については、
            サービスの仕様に従って取り扱います。
        </p>
    </section>

    <section class="privacy-section">
        <h2>4. 個人情報の第三者提供について</h2>

        <p>
            当方は、法令に基づく場合、本人の同意がある場合、
            その他法令で認められる場合を除き、
            個人情報を第三者に提供しません。
        </p>

        <p>
            ただし、サービスの運営に必要な範囲で、
            決済処理、認証、メール送信、データ保存などを
            外部事業者に委託する場合があります。
        </p>

        <p>
            広告配信などに伴う情報の取り扱いについては、
            後述の「広告配信について」に記載します。
        </p>
    </section>

    <section class="privacy-section">
        <h2>5. 個人情報の管理について</h2>

        <p>
            当方は、取得した個人情報について、
            不正アクセス、紛失、漏えい、改ざんなどを防止するため、
            適切な安全管理に努めます。
        </p>

        <p>
            個人情報は利用目的に必要な範囲で保存し、
            保存の必要がなくなった場合は、
            法令その他の事情を考慮して適切に削除または処理します。
        </p>
    </section>

    <section class="privacy-section">
        <h2>6. Cookieの利用について</h2>

        <p>
            当サイトでは、ログイン状態の維持、
            サービスの利便性向上、利用状況の把握、
            広告配信などの目的で、
            Cookie（クッキー）を使用する場合があります。
        </p>

        <p>
            Cookieとは、ウェブサイトを閲覧した際に、
            利用者のブラウザに保存される小さなデータのことです。
        </p>

        <p>
            利用者は、ブラウザの設定によって
            Cookieを無効にすることができます。
        </p>

        <p>
            ただし、Cookieを無効にした場合、
            ログイン機能など、一部のサービスが
            正常に利用できなくなる場合があります。
        </p>
    </section>

    <section class="privacy-section">
        <h2>7. Google AdSenseによる広告配信について</h2>

        <p>
            当サイトでは、第三者配信の広告サービス
            「Google AdSense」を利用する場合があります。
        </p>

        <p>
            Googleなどの第三者配信事業者は、
            Cookieを使用して、利用者が当サイトや
            他のウェブサイトに過去にアクセスした際の情報に基づき、
            広告を配信する場合があります。
        </p>

        <p>
            Googleが広告Cookieを使用することにより、
            Googleおよびそのパートナーは、
            利用者の興味や関心などに応じた広告を
            表示できる場合があります。
        </p>

        <p>
            利用者は、Googleの広告設定から
            パーソナライズド広告を無効にできます。
        </p>

        <ul>
            <li>
                <a href="https://myadcenter.google.com/"
                   target="_blank" rel="noopener noreferrer">
                    Google 広告設定
                </a>
            </li>
            <li>
                <a href="https://policies.google.com/technologies/partner-sites?hl=ja"
                   target="_blank" rel="noopener noreferrer">
                    Googleによる情報の利用について
                </a>
            </li>
            <li>
                <a href="https://www.aboutads.info/"
                   target="_blank" rel="noopener noreferrer">
                    第三者配信事業者の広告設定
                </a>
            </li>
        </ul>

        <p>
            Google以外の第三者配信事業者や広告ネットワークによる
            広告が掲載される場合には、
            それらの事業者によるCookieの利用が行われることがあります。
        </p>
    </section>

    <section class="privacy-section">
        <h2>8. アクセス情報の取得について</h2>

        <p>
            当サイトでは、サービスの運営、
            セキュリティの確保、利用状況の把握などを目的として、
            アクセス日時、閲覧ページ、IPアドレス、
            ブラウザ情報などを取得する場合があります。
        </p>

        <p>
            これらの情報は、サービスの改善、
            不正アクセスの防止、障害対応などに利用します。
        </p>
    </section>

    <section class="privacy-section">
        <h2>9. 外部サービスの利用について</h2>

        <p>
            当サイトでは、サービスの提供に必要な範囲で、
            Google認証、決済、メール送信、
            データ保存、広告配信などの外部サービスを
            利用する場合があります。
        </p>

        <p>
            これらの外部サービスでは、
            各事業者のプライバシーポリシーに従って
            情報が取り扱われる場合があります。
        </p>
    </section>

    <section class="privacy-section">
        <h2>10. 個人情報の開示・訂正・削除について</h2>

        <p>
            本人から個人情報の開示、訂正、削除、
            利用停止などの請求があった場合は、
            本人確認を行ったうえで、
            法令に従い適切に対応します。
        </p>

        <p>
            ただし、法令上の保存義務がある場合など、
            請求に応じられないことがあります。
        </p>
    </section>

    <section class="privacy-section">
        <h2>11. プライバシーポリシーの変更について</h2>

        <p>
            当方は、法令の改正、サービス内容の変更、
            その他必要に応じて、
            本プライバシーポリシーを変更する場合があります。
        </p>

        <p>
            変更後の内容は、当サイト上に掲載した時点から
            適用されるものとします。
            ただし、法令上別途の対応が必要な場合は、
            それに従います。
        </p>
    </section>

    <section class="privacy-section">
        <h2>12. お問い合わせ窓口</h2>

        <p>
            個人情報の取り扱いに関するお問い合わせは、
            以下のメールアドレスまでお願いいたします。
        </p>

        <p>
            <a href="mailto:minawoshi212@yahoo.co.jp">
                minawoshi212@yahoo.co.jp
            </a>
        </p>
    </section>

    <div class="privacy-footer">
        制定・改定日：2026年10月14日
    </div>

</div>

</body>
</html>
""")

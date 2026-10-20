from flask import render_template_string
from urllib.parse import urlencode


def render_nikki_list(
    diaries,
    start_date="",
    end_date="",
    performer="",
    keyword="",
    page=1,
    total_pages=1,
    total_count=0
):

    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>推し活日記全集</title>

    <style>
        body {
            margin: 0;
            padding: 16px;
            background: #fff;
            color: #222;
            font-family: sans-serif;
        }

        .nikki-list-layout {
            width: 100%;
            max-width: 700px;
            margin: 0 auto;
        }

        h2 {
            text-align: center;
            margin: 12px 0 24px;
        }

        .nikki-search {
            margin-bottom: 24px;
            border: 1px solid #ddd;
            border-radius: 6px;
        }

        .nikki-search > summary {
            padding: 14px;
            font-weight: bold;
            background: #f5f5f5;
            cursor: pointer;
        }

        .nikki-search-form {
            padding: 14px;
        }

        .nikki-search-field {
            margin-bottom: 16px;
        }

        .nikki-search-field label {
            display: block;
            font-weight: bold;
            margin-bottom: 6px;
        }

        .nikki-search-field input {
            width: 100%;
            max-width: 100%;
            padding: 9px;
            font-size: 16px;
            box-sizing: border-box;
            border: 1px solid #aaa;
            border-radius: 5px;
        }

        .nikki-date-range {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nikki-date-range input {
            min-width: 0;
            flex: 1;
        }

        .nikki-search-buttons {
            display: flex;
            gap: 10px;
        }

        .nikki-search-buttons button,
        .nikki-search-buttons a {
            padding: 10px 20px;
            border: 1px solid #888;
            border-radius: 5px;
            background: #f5f5f5;
            color: #222;
            font-size: 16px;
            text-decoration: none;
            cursor: pointer;
        }

        .nikki-list-heading {
            margin: 16px 0;
            font-weight: bold;
        }

        .nikki-list-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 16px 4px;
            border-bottom: 1px solid #ddd;
            color: inherit;
            text-decoration: none;
        }

        .nikki-list-item:hover {
            background: #f8f8f8;
        }

        .nikki-list-info {
            flex: 1;
            min-width: 0;
        }

        .nikki-list-date {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .nikki-list-event {
            font-weight: bold;
            margin-bottom: 8px;
            overflow-wrap: anywhere;
        }

        .nikki-list-performers {
            display: flex;
            flex-wrap: wrap;
            gap: 4px 12px;
            color: #555;
            font-size: 14px;
        }

        .nikki-list-performers span {
            white-space: nowrap;
        }

        .nikki-list-thumbnail {
            width: 100px;
            height: 85px;
            flex-shrink: 0;
            background: #eee;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-size: 12px;
        }

        .nikki-list-thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 6px;
        }

        .nikki-list-arrow {
            font-size: 20px;
            color: #888;
        }

        .nikki-list-empty {
            padding: 30px 0;
            text-align: center;
            color: #777;
        }

        @media (max-width: 600px) {
            .nikki-list-thumbnail {
                width: 80px;
                height: 75px;
            }

            .nikki-date-range {
                gap: 4px;
            }
        }

        .nikki-pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin: 24px 0;
        }

        .nikki-pagination a,
        .nikki-pagination .current-page {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 40px;
            min-height: 40px;
            padding: 6px 10px;
            box-sizing: border-box;
            border: 1px solid #888;
            border-radius: 5px;
            color: #222;
            text-decoration: none;
        }

        .nikki-pagination .current-page {
            background: #222;
            color: #fff;
            font-weight: bold;
        }
        
        .nikki-title-row {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 70px;
            margin-bottom: 20px;
        }

        .nikki-title-row h2 {
            margin: 0;
            text-align: center;
        }

        .nikki-back-button {
            position: absolute;
            left: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 70px;
            min-height: 36px;
            padding: 6px 12px;
            box-sizing: border-box;
            border: 1px solid #888;
            border-radius: 6px;
            background: #f5f5f5;
            color: #000;
            font-size: 14px;
            font-weight: bold;
            text-decoration: none;
        }

        .nikki-back-button:hover {
            background: #e5e5e5;
        }
        
        @media (min-width: 701px) {
            .nikki-back-button {
                left: 10px;
            }
        }
    </style>
</head>

<body>
    <main class="nikki-list-layout">

        <div class="nikki-title-row">
            <a href="/schedule" class="nikki-back-button">
                戻る
            </a>
            <h2>推し活日記全集</h2>
        </div>

        <details class="nikki-search"
                 {% if start_date or end_date or performer or keyword %}open{% endif %}>

            <summary>検索</summary>

            <form method="GET" action="/oshikatsu/list"
                  class="nikki-search-form">

                <div class="nikki-search-field">
                    <label>期間検索</label>
                    <div class="nikki-date-range">
                        <input type="date" name="start_date"
                               value="{{ start_date }}">
                        <span>～</span>
                        <input type="date" name="end_date"
                               value="{{ end_date }}">
                    </div>
                </div>

                <div class="nikki-search-field">
                    <label for="performer">出演者検索</label>
                    <input type="text" id="performer"
                           name="performer"
                           value="{{ performer }}"
                           placeholder="出演者名を入力">
                </div>

                <div class="nikki-search-field">
                    <label for="keyword">キーワード検索</label>
                    <input type="text" id="keyword"
                           name="keyword"
                           value="{{ keyword }}"
                           placeholder="イベント名・日記本文など">
                </div>

                <div class="nikki-search-buttons">
                    <button type="submit">検索する</button>
                    <a href="/oshikatsu/list">クリア</a>
                </div>

            </form>
        </details>

        <div class="nikki-list-heading">
            登録した日記（{{ total_count }}件）
        </div>

        {% for diary in diaries %}

            <a class="nikki-list-item"
               href="/oshikatsu/view/{{ diary.id }}">

                <div class="nikki-list-info">

                    <div class="nikki-list-date">
                        {{ diary.event_date.strftime('%-m/%-d') }}
                    </div>

                    <div class="nikki-list-event">
                        {{ diary.event_name }}
                    </div>

                    <div class="nikki-list-performers">
                        {% for name in diary.performers.split() %}
                            <span>{{ name }}</span>
                        {% endfor %}
                    </div>

                </div>

                <div class="nikki-list-thumbnail">
                    {% if diary.thumbnail_id %}
                        <img
                            src="/oshikatsu/photo/{{ diary.thumbnail_id }}"
                            alt="サムネイル"
                            loading="lazy"
                        >
                    {% else %}
                        画像なし
                    {% endif %}
                </div>

                <span class="nikki-list-arrow">›</span>

            </a>

        {% else %}

            <div class="nikki-list-empty">
                登録された日記がありません
            </div>

        {% endfor %}

        {% if total_pages > 1 %}
            <nav class="nikki-pagination" aria-label="ページ切り替え">

                {% if page > 1 %}
                    <a href="{{ page_url }}{{ page - 1 }}">前へ</a>
                {% endif %}

                {% for p in range(1, total_pages + 1) %}
                    {% if p == page %}
                        <span class="current-page">{{ p }}</span>
                    {% else %}
                        <a href="{{ page_url }}{{ p }}">{{ p }}</a>
                    {% endif %}
                {% endfor %}

                {% if page < total_pages %}
                    <a href="{{ page_url }}{{ page + 1 }}">次へ</a>
                {% endif %}

            </nav>
        {% endif %}

    </main>
</body>
</html>
        
    """,
        diaries=[
            {
                "id": row[0],
                "event_date": row[1],
                "event_name": row[2],
                "performers": row[3] or "",
                "thumbnail_id": row[4]
            }
            for row in diaries
        ],
        start_date=start_date,
        end_date=end_date,
        performer=performer,
        keyword=keyword,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        page_url=(
            "/oshikatsu/list?"
            + urlencode({
                "start_date": start_date,
                "end_date": end_date,
                "performer": performer,
                "keyword": keyword
            })
            + "&page="
        )
    )

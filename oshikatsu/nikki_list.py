from flask import render_template_string, request
from urllib.parse import urlencode


def render_nikki_list(
    diaries,
    start_date="",
    end_date="",
    performer="",
    keyword="",
    page=1,
    total_pages=1,
    total_count=0,
    csrf_token=""
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
            background: #eaf5fc;
            color: #23465e;
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
            border: 1px solid #c5dfed;
            border-radius: 12px;
            background: #ffffff;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(35, 100, 145, 0.08);
        }

        .nikki-search > summary {
            padding: 14px 16px;
            font-weight: bold;
            background: #dff1fc;
            color: #23465e;
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
            padding: 16px;
            margin-bottom: 14px;
            background: #fff;
            border: 1px solid #c5dfed;
            border-radius: 12px;
            box-shadow: 0 3px 10px rgba(35, 100, 145, 0.08);
            color: inherit;
            text-decoration: none;
            transition: background 0.2s, box-shadow 0.2s;
        }

        .nikki-list-item:hover {
            background: #f5fbff;
            box-shadow: 0 5px 16px rgba(35, 100, 145, 0.15);
        }

        /* 日記カードのスワイプ領域 */
        .nikki-swipe-container {
            position: relative;
            overflow: hidden;
            margin-bottom: 14px;
            border-radius: 12px;
        }

        .nikki-swipe-container .nikki-list-item {
            position: relative;
            z-index: 1;
            margin-bottom: 0;
            background: #ffffff;
            touch-action: pan-y;
            user-select: none;
            -webkit-user-select: none;
            transition: transform 0.2s ease;
        }

        /* スワイプすると現れる削除ボタン */
        .nikki-swipe-delete {
            position: absolute;
            top: 0;
            right: 0;
            width: 90px;
            height: 100%;
            border: none;
            background: #d9534f;
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }

        .nikki-swipe-delete:hover {
            background: #c9302c;
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

        .site-header {
            margin: -16px -16px 30px;
            background: linear-gradient(to top, #0879d7, #39b9eb);
            color: #fff;
            padding: 18px 12px;
            box-sizing: border-box;
        }

        .site-header-nav {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: nowrap;
            gap: 12px;
            font-size: 14px;
            font-weight: bold;
        }

        @media (max-width: 700px) {
            .site-header {
                padding: 14px 8px;
                margin-bottom: 25px;
            }

            .site-header-nav {
                flex-wrap: nowrap;
                gap: 8px;
                font-size: 12px;
                white-space: nowrap;
            }
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

        .nikki-loading {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: rgba(0, 0, 0, 0.45);
            align-items: center;
            justify-content: center;
        }

        .nikki-loading-box {
            background: #fff;
            padding: 30px 45px;
            border-radius: 10px;
            text-align: center;
            font-size: 18px;
            font-weight: bold;
        }

        .nikki-spinner {
            width: 40px;
            height: 40px;
            margin: 0 auto 20px;
            border: 5px solid #ddd;
            border-top-color: #1689dc;
            border-radius: 50%;
            animation: nikki-spin 0.8s linear infinite;
        }

        @keyframes nikki-spin {
            to {
                transform: rotate(360deg);
            }
        }
    </style>
</head>

<body>
    <header class="site-header">

        <nav class="site-header-nav" style="font-size: 18px;">
            <a href="/oshikatsu/purpose" style="color: inherit; text-decoration: none;">目的</a>
            <a href="/schedule" style="color: inherit; text-decoration: none;">イベスケ</a>
        </nav>
    </header>

    <main class="nikki-list-layout">
        <div class="nikki-title-row">
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

            <div class="nikki-swipe-container" data-diary-id="{{ diary.id }}">

                <button type="button"
                        class="nikki-swipe-delete"
                        data-diary-id="{{ diary.id }}">
                    削除
                </button>

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

            </div>

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
    
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            if (document.cookie.includes("oshi_save_success=1")) {
                alert("推し活日記を保存しました");
                document.cookie = "oshi_save_success=; path=/oshikatsu; max-age=0";
            }

            if (document.cookie.includes("oshi_delete_success=1")) {
                alert("推し活日記を削除しました");
                document.cookie = "oshi_delete_success=; path=/oshikatsu; max-age=0";
            }
        });
    </script>
    
    <div id="nikki-loading" class="nikki-loading">
        <div class="nikki-loading-box">
            <div class="nikki-spinner"></div>
        </div>
    </div>

    <script>
        const nikkiLoading = document.getElementById("nikki-loading");
        const swipeWidth = 90;

        document.querySelectorAll(".nikki-swipe-container").forEach(function (container) {
            const card = container.querySelector(".nikki-list-item");

            let startX = 0;
            let startY = 0;
            let startOffset = 0;
            let currentOffset = 0;
            let dragging = false;
            let moved = false;
            let suppressClick = false;

            card.addEventListener("pointerdown", function (e) {
                if (e.pointerType === "mouse" && e.button !== 0) return;

                startX = e.clientX;
                startY = e.clientY;
                startOffset = currentOffset;
                dragging = true;
                moved = false;
                suppressClick = false;

                // PCではカードの外にマウスが出ても操作を追跡
                if (e.pointerType === "mouse") {
                    card.setPointerCapture(e.pointerId);
                }
            });

            card.addEventListener("pointermove", function (e) {
                if (!dragging) return;

                const dx = e.clientX - startX;
                const dy = e.clientY - startY;

                if (!moved && Math.abs(dy) > Math.abs(dx)) {
                    return;
                }

                if (Math.abs(dx) > 8) {
                    moved = true;
                    suppressClick = true;
                }

                if (!moved) return;

                if (e.pointerType === "mouse" && e.buttons !== 1) return;

                const nextOffset = Math.max(
                    -swipeWidth,
                    Math.min(0, startOffset + dx)
                );

                currentOffset = nextOffset;
                card.style.transition = "none";
                card.style.transform = `translateX(${currentOffset}px)`;
            });

            function finishSwipe() {
                if (!dragging) return;

                dragging = false;

                if (!moved) return;

                currentOffset = currentOffset < -45 ? -swipeWidth : 0;

                card.style.transition = "transform 0.2s ease";
                card.style.transform = `translateX(${currentOffset}px)`;
            }

            card.addEventListener("pointerup", finishSwipe);

            card.addEventListener("pointercancel", function () {
                if (!dragging) return;

                dragging = false;

                // 操作が中断された場合は開始前の位置に戻す
                currentOffset = startOffset;

                card.style.transition = "transform 0.2s ease";
                card.style.transform = `translateX(${currentOffset}px)`;
            });

            card.addEventListener("dragstart", function (e) {
                e.preventDefault();
            });
            
            card.addEventListener("click", function (e) {
                if (suppressClick) {
                    e.preventDefault();
                    suppressClick = false;
                    return;
                }

                if (currentOffset !== 0) {
                    e.preventDefault();

                    currentOffset = 0;
                    card.style.transition = "transform 0.2s ease";
                    card.style.transform = "translateX(0px)";
                    return;
                }

                nikkiLoading.style.display = "flex";
            });

            // 削除ボタンを押したときの確認処理
            const deleteButton = container.querySelector(".nikki-swipe-delete");

            deleteButton.addEventListener("click", function () {
                const diaryId = deleteButton.dataset.diaryId;

                const confirmed = window.confirm(
                    "この日記を削除しますか？\\n削除すると元に戻せません。"
                );

                if (!confirmed) {
                    return;
                }

                // 削除リクエストをPOSTで送信
                const form = document.createElement("form");
                form.method = "POST";
                form.action = "/oshikatsu/delete/" + encodeURIComponent(diaryId);

                // CSRFトークン
                const csrfInput = document.createElement("input");
                csrfInput.type = "hidden";
                csrfInput.name = "csrf_token";
                csrfInput.value = "{{ csrf_token }}";

                form.appendChild(csrfInput);
                document.body.appendChild(form);

                // 二重送信を防止
                deleteButton.disabled = true;

                // 削除処理中のローディングを表示
                nikkiLoading.style.display = "flex";

                form.submit();
            });
        });

        window.addEventListener("pageshow", function () {
            nikkiLoading.style.display = "none";
        });            

    </script>

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
        ),
        csrf_token=csrf_token
    )

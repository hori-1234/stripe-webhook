from flask import render_template_string
from oshikatsu.nikki_photo import render_nikki_photo_form
from oshikatsu.nikki_layout import render_nikki_layout


def render_nikki_form(logged_in, csrf_token=""):
    photo_form = render_nikki_photo_form()
    diary_layout = render_nikki_layout(mode="input")
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>推し活日記</title>

    <style>
        .nikki-back-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            text-decoration: none;
        }

        .nikki-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .nikki-demo-label {
            display: inline-block;
            background: #000;
            color: #fff;
            font-size: 1em;
            font-weight: bold;
            padding: 3px 10px;
            white-space: nowrap;
        }
    
        .login-button {
            display: inline-block;
            padding: 6px 12px;
            border: 1px solid #888;
            background: #f5f5f5;
            color: #000;
            text-decoration: none;
            font-size: 13px;
        }

        .login-button:hover {
            background: #e5e5e5;
        }

        .nikki-demo-button {
            min-width: 150px;
            min-height: 48px;
            padding: 10px 24px;
            font-size: 18px;
            font-weight: bold;
            border: 1px solid #888;
            border-radius: 6px;
            background: #f5f5f5;
            color: #000;
            cursor: pointer;
        }

        .nikki-demo-button:hover {
            background: #e5e5e5;
        }
    </style>
</head>

<body>
    <h2 class="nikki-title">
        推し活日記
        {% if not logged_in %}
            <span class="nikki-demo-label" id="nikki-demo-label">デモ画面(編集)</span>
        {% endif %}
    </h2>

    {% if logged_in %}
    
        <p>ログイン中</p>
    {% else %}
        <p>未ログイン：入力内容は保存できません。</p>
         <a href="/schedule/login" class="login-button" id="nikki-login-button">新規登録・ログイン</a>
    {% endif %}

    <form method="POST" action="/oshikatsu/save" enctype="multipart/form-data">
        {% if logged_in %}
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        {% endif %}

        {{ diary_layout }}
        
        {{ photo_form }}

        {% if logged_in %}
            <p><button type="submit">保存</button></p>
        {% else %}
            <p><button type="button" id="demo-preview-button" class="nikki-demo-button">プレビュー</button></p>
        {% endif %}
    </form>

    {% if not logged_in %}
    
    <div id="demo-preview-screen" hidden>
        <div class="demo-preview-layout">

            <div class="demo-preview-date-place">
                <div>
                    <strong>日付</strong>
                    <div class="demo-preview-value" id="demo-event-date"></div>
                </div>
                <div>
                    <strong>場所</strong>
                    <div class="demo-preview-value" id="demo-place"></div>
                </div>
            </div>

            <p><strong>イベント名</strong></p>
            <div class="demo-preview-value" id="demo-event-name"></div>

            <p><strong>出演者</strong></p>
            <div class="demo-preview-value" id="demo-performers"></div>

            <details class="demo-diary-first">
    <summary aria-label="日記を表示">
        <span class="demo-diary-first-guide">
            ※日記は折りたたんで表示できます
        </span>
    </summary>

    <details class="demo-diary-second">
        <summary>
            日記(本文)
            <span class="demo-diary-second-guide">
                ※タップすると本文を表示
            </span>
        </summary>

        <div class="demo-preview-value" id="demo-diary-text"></div>
    </details>
</details>

            <div id="demo-preview-photos"></div>
        </div>

        <p><button type="button" id="demo-preview-back" class="nikki-demo-button">編集画面</button></p>
    </div>

    <div class="demo-photo-lightbox" id="demo-photo-lightbox"
         role="dialog" aria-modal="true" aria-label="写真の拡大表示">

        <button type="button" class="demo-photo-close"
                id="demo-photo-close" aria-label="閉じる">×</button>

        <button type="button" class="demo-photo-arrow demo-photo-prev"
                id="demo-photo-prev" aria-label="前の写真">＜</button>

        <img id="demo-photo-enlarged" alt="拡大写真">

        <div class="demo-photo-loading" id="demo-photo-loading">
            <div class="demo-photo-spinner"></div>
        </div>

        <button type="button" class="demo-photo-arrow demo-photo-next"
        
                id="demo-photo-next" aria-label="次の写真">＞</button>

        <div class="demo-photo-counter" id="demo-photo-counter"></div>
    </div>

    <style>

        .demo-preview-layout {
            width: 100%;
            max-width: 700px;
        }

        .demo-preview-date-place {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }

        .demo-preview-value {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #f8f8f8;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            min-height: 20px;
        }

        .demo-preview-layout strong {
            display: block;
            margin-bottom: 5px;
        }

        .demo-diary-first {
            margin: 20px 0;
        }

        .demo-diary-first > summary {
            list-style: none;
            text-align: center;
            cursor: pointer;
            padding: 12px;
        }

        .demo-diary-first > summary::-webkit-details-marker {
            display: none;
        }

        .demo-diary-first > summary::after {
            content: "▼";
        }

        .demo-diary-first[open] > summary::after {
            content: "▲";
        }

        .demo-diary-second {
            margin-top: 10px;
        }

        .demo-diary-second > summary {
            cursor: pointer;
            font-weight: bold;
            padding: 10px;
        }

        .demo-diary-first-guide,
        .demo-diary-second-guide {
            font-size: 12px;
            font-weight: normal;
            color: #777;
            margin-left: 8px;
        }

        /* 1段階開いたら、最初の説明を非表示 */
        .demo-diary-first[open] > summary .demo-diary-first-guide {
            display: none;
        }

        /* 本文を開いたら、2段階目の説明を非表示 */
        .demo-diary-second[open] > summary .demo-diary-second-guide {
            display: none;
        }
        
        #demo-preview-photos {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 12px;
            margin-top: 20px;
        }

        .demo-preview-photo img {
            width: 100%;
            aspect-ratio: 1;
            object-fit: cover;
            border-radius: 6px;
            cursor: pointer;
        }

        .demo-preview-photo p {
            text-align: center;
            font-size: 13px;
        }

        #demo-preview-screen[hidden] {
            display: none;
        }

        .demo-photo-lightbox {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 99999;
            background: rgba(0, 0, 0, 0.95);
            align-items: center;
            justify-content: center;
        }

        .demo-photo-lightbox.is-open {
            display: flex;
        }

        .demo-photo-lightbox img {
            max-width: 90vw;
            max-height: 85vh;
            object-fit: contain;
        }

        .demo-photo-close {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 40px;
            color: white;
            background: none;
            border: none;
            cursor: pointer;
        }

        .demo-photo-arrow {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 60px;
            height: 85px;
            font-size: 42px;
            color: white;
            background: rgba(0, 0, 0, 0.3);
            border: none;
            cursor: pointer;
        }

        .demo-photo-prev {
            left: 5px;
        }

        .demo-photo-next {
            right: 5px;
        }

        .demo-photo-arrow:disabled {
            display: none;
        }

        .demo-photo-arrow.is-hidden {
            opacity: 0;
            pointer-events: none;
        }

        .demo-photo-arrow {
            transition: opacity 0.3s ease;
        }

        .demo-photo-counter {
            position: absolute;
            bottom: 20px;
            color: white;
            font-size: 16px;
        }

        .demo-photo-loading {
            display: none;
            position: absolute;
            inset: 0;
            align-items: center;
            justify-content: center;
            pointer-events: none;
        }

        .demo-photo-loading.is-loading {
            display: flex;
        }

        .demo-photo-spinner {
            width: 52px;
            height: 52px;
            border: 6px solid rgba(255, 255, 255, 0.25);
            border-top: 6px solid #ffffff;
            border-radius: 50%;
            animation: demo-photo-spin 0.8s linear infinite;
        }

        @keyframes demo-photo-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }


        @media (max-width: 600px) {
            .demo-photo-arrow {
                width: 50px;
                height: 75px;
                font-size: 36px;
            }
        }
    </style>

    <script>
        document.addEventListener("DOMContentLoaded", function () {
            const form = document.querySelector('form[action="/oshikatsu/save"]');
            const previewButton = document.getElementById("demo-preview-button");
            const previewScreen = document.getElementById("demo-preview-screen");
            const backButton = document.getElementById("demo-preview-back");

            if (!form || !previewButton || !previewScreen || !backButton) {
                return;
            }

            const title = document.querySelector("body > h2");
            const demoLabel = document.getElementById("nikki-demo-label");
            const loginNotice = form.previousElementSibling;
            const returnLink = document.getElementById("nikki-schedule-back");
            const loginButton = document.getElementById("nikki-login-button");

            function getValue(name) {
                const field = form.elements.namedItem(name);
                return field ? field.value : "";
            }

            previewButton.addEventListener("click", function () {
                const fields = {
                    "demo-event-date": "event_date",
                    "demo-place": "place",
                    "demo-event-name": "event_name",
                    "demo-performers": "performers",
                    "demo-diary-text": "diary_text"
                };

                Object.keys(fields).forEach(function (id) {
                    document.getElementById(id).textContent = getValue(fields[id]);
                });

                const photosContainer = document.getElementById("demo-preview-photos");

                previewPhotoUrls.forEach(function (url) {
                    URL.revokeObjectURL(url);
                });
                previewPhotoUrls = [];

                photosContainer.replaceChildren();

                const photoInput = document.getElementById("nikki-photo-input");
                const files = photoInput ? Array.from(photoInput.files) : [];

                files.forEach(function (file, index) {
                    const item = document.createElement("div");
                    item.className = "demo-preview-photo";

                    const image = document.createElement("img");
                    const url = URL.createObjectURL(file);

                    previewPhotoUrls.push(url);

                    image.src = url;
                    image.alt = "画像" + (index + 1);

                    const label = document.createElement("p");
                    label.textContent = index === 0
                        ? "画像1（サムネ）"
                        : "画像" + (index + 1);

                    item.appendChild(image);
                    item.appendChild(label);
                    photosContainer.appendChild(item);
                });

                previewScreen.querySelectorAll("details").forEach(function (element) {
                    element.open = false;
                });

                form.hidden = true;
                previewScreen.hidden = false;

                if (demoLabel) demoLabel.textContent = "デモ画面(プレビュー)";
                if (returnLink) returnLink.hidden = true;
                if (loginButton) loginButton.hidden = true;
                window.scrollTo(0, 0);
            });

            backButton.addEventListener("click", function () {
                previewScreen.hidden = true;
                form.hidden = false;

                if (demoLabel) demoLabel.textContent = "デモ画面(編集)";
                if (returnLink) returnLink.hidden = false;
                if (loginButton) loginButton.hidden = false;
                window.scrollTo(0, 0);
            });

            const lightbox = document.getElementById("demo-photo-lightbox");
            const enlarged = document.getElementById("demo-photo-enlarged");
            const closeButton = document.getElementById("demo-photo-close");
            const prevButton = document.getElementById("demo-photo-prev");
            const nextButton = document.getElementById("demo-photo-next");
            const counter = document.getElementById("demo-photo-counter");

            const photoLoading = document.getElementById("demo-photo-loading");

            let currentPhotoIndex = 0;
            let previewPhotoUrls = [];
            let arrowHideTimer = null;

            function showPhotoArrows() {
                prevButton.classList.remove("is-hidden");
                nextButton.classList.remove("is-hidden");

                clearTimeout(arrowHideTimer);

                arrowHideTimer = setTimeout(function () {
                    prevButton.classList.add("is-hidden");
                    nextButton.classList.add("is-hidden");
                }, 3000);
            }

            enlarged.addEventListener("load", function () {
            
                photoLoading.classList.remove("is-loading");
                enlarged.style.visibility = "visible";
            });

            enlarged.addEventListener("error", function () {
                photoLoading.classList.remove("is-loading");
                enlarged.style.visibility = "hidden";
            });

            function showDemoPhoto(index) {
                if (index < 0 || index >= previewPhotoUrls.length) {
                    return;
                }

                currentPhotoIndex = index;

                enlarged.style.visibility = "hidden";
                photoLoading.classList.add("is-loading");

                enlarged.src = previewPhotoUrls[index];

                if (enlarged.complete) {
                    photoLoading.classList.remove("is-loading");
                    enlarged.style.visibility = enlarged.naturalWidth > 0
                        ? "visible"
                        : "hidden";
                }

                counter.textContent =
                    (index + 1) + " / " + previewPhotoUrls.length;

                prevButton.disabled = index === 0;
                nextButton.disabled = index === previewPhotoUrls.length - 1;

                showPhotoArrows();
            }

            function closeDemoPhoto() {
                clearTimeout(arrowHideTimer);
                lightbox.classList.remove("is-open");
                enlarged.removeAttribute("src");
                document.body.style.overflow = "";
            }

            document.getElementById("demo-preview-photos")
                .addEventListener("click", function (event) {
                    const clickedImage = event.target.closest("img");

                    if (!clickedImage) {
                        return;
                    }

                    const images = Array.from(
                        document.querySelectorAll("#demo-preview-photos img")
                    );

                    previewPhotoUrls = images.map(function (image) {
                        return image.src;
                    });

                    const index = images.indexOf(clickedImage);

                    if (index === -1) {
                        return;
                    }

                    showDemoPhoto(index);
                    lightbox.classList.add("is-open");
                    document.body.style.overflow = "hidden";
                });

            closeButton.addEventListener("click", closeDemoPhoto);

            enlarged.addEventListener("click", function () {
                showPhotoArrows();
            });

            prevButton.addEventListener("click", function () {
            
                showDemoPhoto(currentPhotoIndex - 1);
            });

            nextButton.addEventListener("click", function () {
                showDemoPhoto(currentPhotoIndex + 1);
            });

            lightbox.addEventListener("click", function (event) {
                if (event.target === lightbox) {
                    closeDemoPhoto();
                }
            });

            document.addEventListener("keydown", function (event) {
                if (!lightbox.classList.contains("is-open")) {
                    return;
                }

                if (event.key === "Escape") {
                    closeDemoPhoto();
                } else if (event.key === "ArrowLeft") {
                    showDemoPhoto(currentPhotoIndex - 1);
                } else if (event.key === "ArrowRight") {
                    showDemoPhoto(currentPhotoIndex + 1);
                }
            });
        });
    </script>
    {% endif %}
    
    <p id="nikki-schedule-back">
        <a href="/schedule" class="nikki-demo-button nikki-back-button">
            イベスケに戻る
        </a>
    </p>

</body>
</html>
    """, logged_in=logged_in, csrf_token=csrf_token, photo_form=photo_form, diary_layout=diary_layout)


def render_nikki_view(
    diary,
    photo_view="",
    diary_id=None,
    prev_diary_id=None,
    next_diary_id=None
):    
    diary_layout = render_nikki_layout(
        diary=diary,
        mode="view"
    )

    return render_template_string("""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>推し活日記 - 閲覧</title>

    <style>
        .nikki-view-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            max-width: 700px;
            gap: 12px;
        }

        .nikki-view-header h2 {
            margin: 16px 0;
            text-align: center;
        }

        .nikki-move-button,
        .nikki-move-empty {
            width: 50px;
            height: 60px;
            flex-shrink: 0;
        }

        .nikki-move-button {
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: #222;
            background: rgba(128, 128, 128, 0.15);
            border-radius: 6px;
            text-decoration: none;
        }

        .nikki-move-button:hover {
            background: rgba(128, 128, 128, 0.3);
        }

        .nikki-action-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            min-width: 150px;
            min-height: 48px;
            padding: 10px 24px;
            font-size: 18px;
            font-weight: bold;
            border: 1px solid #888;
            border-radius: 6px;
            background: #f5f5f5;
            color: #000;
            text-decoration: none;
            cursor: pointer;
        }

        .nikki-action-button:hover {
            background: #e5e5e5;
        }



        .nikki-page-loading {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 100000;
            background: rgba(0, 0, 0, 0.65);
            align-items: center;
            justify-content: center;
        }

        .nikki-page-loading.is-loading {
            display: flex;
        }

        .nikki-page-loading-spinner {
            width: 52px;
            height: 52px;
            border: 6px solid rgba(255, 255, 255, 0.25);
            border-top: 6px solid #ffffff;
            border-radius: 50%;
            animation: nikki-page-spin 0.8s linear infinite;
        }

        @keyframes nikki-page-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>
</head>

<body>
    <div class="nikki-view-header">
        {% if prev_diary_id is not none %}
            <a href="/oshikatsu/view/{{ prev_diary_id }}"
               class="nikki-move-button"
               aria-label="前の日記">＜</a>
        {% else %}
            <span class="nikki-move-empty"></span>
        {% endif %}

        <h2>推し活日記</h2>

        {% if next_diary_id is not none %}
            <a href="/oshikatsu/view/{{ next_diary_id }}"
               class="nikki-move-button"
               aria-label="次の日記">＞</a>
        {% else %}
            <span class="nikki-move-empty"></span>
        {% endif %}
    </div>

    {{ diary_layout }}

    {{ photo_view }}

     <p>
        <a href="/oshikatsu/edit/{{ diary_id }}" class="nikki-action-button">
            編集
        </a>
    </p>
    
    <p>
        <a href="/schedule" class="nikki-action-button">
            イベスケに戻る
        </a>
    </p>

    <div class="nikki-page-loading" id="nikki-page-loading">
        <div class="nikki-page-loading-spinner"></div>
    </div>

    <script>
        document.querySelectorAll(".nikki-move-button").forEach(function (button) {
            button.addEventListener("click", function () {
                document.getElementById("nikki-page-loading")
                    .classList.add("is-loading");
            });
        });

        window.addEventListener("pageshow", function () {
            document.getElementById("nikki-page-loading")
                .classList.remove("is-loading");
        });
    </script>
</body>
</html>
    """,
        diary_layout=diary_layout,
        photo_view=photo_view,
        diary_id=diary_id,
        prev_diary_id=prev_diary_id,
        next_diary_id=next_diary_id                          
    )

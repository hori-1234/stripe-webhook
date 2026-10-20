
from markupsafe import Markup

from oshikatsu.oshi_photo_list import get_oshi_diary_photos


def render_nikki_photo_view(diary_id, user_id):

    photos = get_oshi_diary_photos(
        diary_id=diary_id,
        user_id=user_id
    )

    if not photos:
        return Markup("")

    html = """
    <style>
        .nikki-photo-view {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }

        .nikki-photo-view img {
            width: 150px;
            height: 150px;
            object-fit: cover;
            border-radius: 6px;
            cursor: pointer;
        }

        .nikki-photo-lightbox {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 99999;
            background: rgba(0, 0, 0, 0.95);
            align-items: center;
            justify-content: center;
        }

        .nikki-photo-lightbox.is-open {
            display: flex;
        }

        .nikki-photo-lightbox-image {
            max-width: 100vw;
            max-height: 100dvh;
            width: auto;
            height: auto;
            object-fit: contain;
        }

        .nikki-photo-lightbox-close,
        .nikki-photo-lightbox-prev,
        .nikki-photo-lightbox-next {
            position: absolute;
            z-index: 2;
            border: none;
            background: rgba(0, 0, 0, 0.5);
            color: white;
            cursor: pointer;
            font-size: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .nikki-photo-lightbox-close {
            top: 12px;
            right: 12px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
        }

        .nikki-photo-lightbox-prev,
        .nikki-photo-lightbox-next {
            top: 50%;
            transform: translateY(-50%);
            width: 60px;
            height: 85px;
            font-size: 42px;
            background: rgba(0, 0, 0, 0.3);
        }

        .nikki-photo-lightbox-prev {
            left: 0;
        }

        .nikki-photo-lightbox-next {
            right: 0;
        }

        .nikki-photo-lightbox-counter {
            position: absolute;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%);
            color: white;
            font-size: 14px;
            background: rgba(0, 0, 0, 0.5);
            padding: 6px 12px;
            border-radius: 20px;
        }

        @media (max-width: 600px) {
            .nikki-photo-lightbox-prev,
            .nikki-photo-lightbox-next {
                width: 50px;
                height: 75px;
                font-size: 36px;
            }
        }

        
        .nikki-photo-loading {
            position: absolute;
            inset: 0;
            z-index: 1;
            display: none;
            align-items: center;
            justify-content: center;
            pointer-events: none;
        }

        .nikki-photo-loading.is-loading {
            display: flex;
        }

        .nikki-photo-loading-spinner {
            width: 52px;
            height: 52px;
            border: 6px solid rgba(255, 255, 255, 0.25);
            border-top: 6px solid #ffffff;
            border-radius: 50%;
            animation: nikki-photo-loading-spin 0.8s linear infinite;
        }

        @keyframes nikki-photo-loading-spin {
            from {
                transform: rotate(0deg);
            }
            to {
                transform: rotate(360deg);
            }
        }
        
    </style>

    <div class="nikki-photo-view">
    """

    for photo_id, photo_order in photos:

        label = "（サムネ）" if photo_order == 1 else ""

        html += f"""
        <div>
            <img
                src="/oshikatsu/photo/{photo_id}"
                alt="画像{photo_order}{label}"
                loading="lazy"
            >
            <div>画像{photo_order}{label}</div>
        </div>
        """

    html += """
    </div>

    <div class="nikki-photo-lightbox" role="dialog"
         aria-modal="true" aria-label="写真の拡大表示">

        <button type="button"
                class="nikki-photo-lightbox-close"
                aria-label="閉じる">×</button>

        <button type="button"
                class="nikki-photo-lightbox-prev"
                aria-label="前の写真">＜</button>

        <div class="nikki-photo-loading">
            <div class="nikki-photo-loading-spinner"></div>
        </div>

        <img class="nikki-photo-lightbox-image" alt="拡大写真">

        <button type="button"
                class="nikki-photo-lightbox-next"
                aria-label="次の写真">＞</button>

        <div class="nikki-photo-lightbox-counter"></div>
    </div>

    <script>
    (function () {
        const gallery = document.querySelector(".nikki-photo-view");
        const lightbox = document.querySelector(".nikki-photo-lightbox");

        if (!gallery || !lightbox) {
            return;
        }

        const images = Array.from(gallery.querySelectorAll("img"));
        const enlarged = lightbox.querySelector(
            ".nikki-photo-lightbox-image"
        );
        const closeButton = lightbox.querySelector(
            ".nikki-photo-lightbox-close"
        );
        const prevButton = lightbox.querySelector(
            ".nikki-photo-lightbox-prev"
        );
        const nextButton = lightbox.querySelector(
            ".nikki-photo-lightbox-next"
        );
        const counter = lightbox.querySelector(
            ".nikki-photo-lightbox-counter"
        );

        let currentIndex = 0;
        let previousOverflow = "";

        function showImage(index) {
        
        const loading = lightbox.querySelector(
            ".nikki-photo-loading"
        );

        currentIndex = (index + images.length) % images.length;

            const source = images[currentIndex];

            enlarged.style.visibility = "hidden";
            loading.classList.add("is-loading");

            enlarged.onload = function () {
                loading.classList.remove("is-loading");
                enlarged.style.visibility = "visible";
            };

            enlarged.onerror = function () {
                loading.classList.remove("is-loading");
            };

            enlarged.alt = source.alt;
            enlarged.src = source.src;

            if (enlarged.complete && enlarged.naturalWidth > 0) {
                loading.classList.remove("is-loading");
                enlarged.style.visibility = "visible";
            }

            counter.textContent =
                (currentIndex + 1) + " / " + images.length;

            const multiple = images.length > 1;
            prevButton.style.display = multiple ? "flex" : "none";
            nextButton.style.display = multiple ? "flex" : "none";
        }

        function openLightbox(index) {
            previousOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
            lightbox.classList.add("is-open");
            showImage(index);
        }

        function closeLightbox() {
            lightbox.classList.remove("is-open");
            document.body.style.overflow = previousOverflow;
            enlarged.removeAttribute("src");
        }

        images.forEach(function (img, index) {
            img.addEventListener("click", function () {
                openLightbox(index);
            });
        });

        closeButton.addEventListener("click", closeLightbox);

        prevButton.addEventListener("click", function () {
            showImage(currentIndex - 1);
        });

        nextButton.addEventListener("click", function () {
            showImage(currentIndex + 1);
        });

        lightbox.addEventListener("click", function (event) {
            if (event.target === lightbox) {
                closeLightbox();
            }
        });

        document.addEventListener("keydown", function (event) {
            if (!lightbox.classList.contains("is-open")) {
                return;
            }

            if (event.key === "Escape") {
                closeLightbox();
            } else if (event.key === "ArrowLeft") {
                showImage(currentIndex - 1);
            } else if (event.key === "ArrowRight") {
                showImage(currentIndex + 1);
            }
        });

        let touchStartX = null;

        lightbox.addEventListener("touchstart", function (event) {
            if (event.touches.length === 1) {
                touchStartX = event.touches[0].clientX;
            }
        }, { passive: true });

        lightbox.addEventListener("touchend", function (event) {
            if (touchStartX === null) {
                return;
            }

            const difference =
                event.changedTouches[0].clientX - touchStartX;

            touchStartX = null;

            if (Math.abs(difference) < 50 || images.length < 2) {
                return;
            }

            showImage(currentIndex + (difference < 0 ? 1 : -1));
        }, { passive: true });
    })();
    </script>
    """

    return Markup(html)

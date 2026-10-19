import json

from markupsafe import Markup


def render_nikki_photo_form(saved_photos=None):
    if saved_photos is None:
        saved_photos = []

    saved_photos_json = json.dumps(
        saved_photos,
        ensure_ascii=False
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    html = """
    <div class="nikki-photo-section">
        <h3>写真（最大10枚）</h3>

        <div id="nikki-photo-preview"></div>

        <p id="nikki-photo-count">選択中：0 / 10枚</p>

        <input
            type="file"
            id="nikki-photo-input"
            name="photos"
            accept="image/*"
            multiple
            hidden
        >
    </div>

    <style>
        #nikki-photo-preview {
            display: grid;
            grid-template-columns: repeat(
                auto-fill,
                minmax(120px, 1fr)
            );
            gap: 12px;
            margin-top: 15px;
        }

        .nikki-photo-item {
            position: relative;
            min-width: 0;
        }

        .nikki-photo-box {
            width: 100%;
            aspect-ratio: 1;
            border: 2px dashed #aaa;
            border-radius: 8px;
            box-sizing: border-box;
            background: #f8f8f8;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            overflow: hidden;
        }

        .nikki-photo-box img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .nikki-photo-add {
            font-size: 40px;
            color: #777;
        }

        .nikki-photo-remove {
            position: absolute;
            top: 5px;
            right: 5px;
            width: 28px;
            height: 28px;
            border: none;
            border-radius: 50%;
            background: #e83e75;
            color: white;
            font-size: 20px;
            cursor: pointer;
            z-index: 1;
        }

        .nikki-photo-item p {
            text-align: center;
            margin: 5px 0;
            font-size: 13px;
        }
    </style>

    <script>
        document.addEventListener("DOMContentLoaded", function () {
            const input = document.getElementById(
                "nikki-photo-input"
            );

            const preview = document.getElementById(
                "nikki-photo-preview"
            );

            const count = document.getElementById(
                "nikki-photo-count"
            );

            let photos = [];
            let editingIndex = null;

            const savedPhotosElement = document.getElementById(
                "nikki-saved-photos"
            );

            const savedPhotos = savedPhotosElement
                ? JSON.parse(savedPhotosElement.textContent)
                : [];

            function updateFiles() {
                const dataTransfer = new DataTransfer();

                photos.forEach(function (file) {
                    dataTransfer.items.add(file);
                });

                input.files = dataTransfer.files;

                count.textContent =
                    "選択中：" + photos.length + " / 10枚";
            }

            function renderPhotos() {
                preview.innerHTML = "";

                savedPhotos.forEach(function (photo, index) {
                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";

                    const box = document.createElement("div");
                    box.className = "nikki-photo-box";

                    const img = document.createElement("img");
                    img.src = photo.url;
                    img.alt = "保存済み画像" + (index + 1);

                    box.appendChild(img);

                    const label = document.createElement("p");
                    label.textContent = index === 0
                        ? "画像1（サムネ）"
                        : "画像" + (index + 1);

                    item.appendChild(box);
                    item.appendChild(label);
                    preview.appendChild(item);
                });

                photos.forEach(function (file, index) {

                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";

                    const box = document.createElement("div");
                    box.className = "nikki-photo-box";

                    const img = document.createElement("img");
                    const url = URL.createObjectURL(file);

                    img.src = url;
                    img.onload = function () {
                        URL.revokeObjectURL(url);
                    };

                    box.appendChild(img);

                    box.addEventListener("click", function () {
                        editingIndex = index;
                        input.click();
                    });

                    const remove = document.createElement("button");
                    remove.type = "button";
                    remove.className = "nikki-photo-remove";
                    remove.textContent = "×";

                    remove.addEventListener("click", function () {
                        photos.splice(index, 1);
                        updateFiles();
                        renderPhotos();
                    });

                    const label = document.createElement("p");

                    label.textContent = index === 0
                        ? "画像1（サムネ）"
                        : "画像" + (index + 1);

                    item.appendChild(box);
                    item.appendChild(remove);
                    item.appendChild(label);

                    preview.appendChild(item);
                });

                if (photos.length < 10) {
                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";

                    const add = document.createElement("div");
                    add.className = "nikki-photo-box";

                    const plus = document.createElement("span");
                    plus.className = "nikki-photo-add";
                    plus.textContent = "+";

                    add.appendChild(plus);

                    add.addEventListener("click", function () {
                        editingIndex = null;
                        input.click();
                    });

                    item.appendChild(add);
                    preview.appendChild(item);
                }
            }

            input.addEventListener("change", function () {
                const selected = Array.from(input.files);

                if (selected.length === 0) {
                    return;
                }

                const valid = selected.filter(function (file) {
                    return file.type.startsWith("image/");
                });

                if (valid.length !== selected.length) {
                    alert("画像ファイルのみ選択できます");
                }

                if (editingIndex !== null) {
                    if (valid.length > 0) {
                        photos[editingIndex] = valid[0];
                    }

                    editingIndex = null;
                } else {
                    const remaining = Math.max(
                        0,
                        10 - savedPhotos.length - photos.length
                    );

                    if (valid.length > remaining) {
                        alert("写真は最大10枚までです");
                    }

                    photos.push(...valid.slice(0, remaining));
                }

                updateFiles();
                renderPhotos();
            });

            renderPhotos();
        });
    </script>
    """

    html += f"""
    <script type="application/json" id="nikki-saved-photos">
{saved_photos_json}
    </script>
    """

    return Markup(html)

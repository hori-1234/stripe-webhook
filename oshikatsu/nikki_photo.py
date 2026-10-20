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
            let editingSavedIndex = null;

            const savedPhotosElement = document.getElementById(
                "nikki-saved-photos"
            );

            const savedPhotos = savedPhotosElement
                ? JSON.parse(savedPhotosElement.textContent)
                : [];

            const removedPhotoIds = [];

            function updateFiles() {
                const dataTransfer = new DataTransfer();

                photos.forEach(function (file) {
                    dataTransfer.items.add(file);
                });

                input.files = dataTransfer.files;

                count.textContent =
                    "写真：" + (savedPhotos.length + photos.length) + " / 10枚";

                document.querySelectorAll(
                    'input[name="remove_photo_ids"]'
                ).forEach(function (element) {
                    element.remove();
                });

                const form = input.closest("form");

                if (form) {
                    removedPhotoIds.forEach(function (photoId) {
                        const hidden = document.createElement("input");
                        hidden.type = "hidden";
                        hidden.name = "remove_photo_ids";
                        hidden.value = photoId;

                        form.appendChild(hidden);
                    });

                    form.querySelectorAll(
                        'input[name="photo_order_data"]'
                    ).forEach(function (element) {
                        element.remove();
                    });

                    const orderInput = document.createElement("input");
                    orderInput.type = "hidden";
                    orderInput.name = "photo_order_data";

                    form.appendChild(orderInput);

                    form.onsubmit = function () {
                        const photoOrderData = Array.from(
                            preview.querySelectorAll(".nikki-photo-item")
                        ).filter(function (item) {
                            return item.querySelector("img") !== null;
                        }).map(function (item, index) {
                            return {
                                photo_id: item.dataset.photoId || null,
                                new_photo_index:
                                    item.dataset.newPhotoIndex !== undefined
                                        ? Number(item.dataset.newPhotoIndex)
                                        : null,
                                photo_order: index + 1
                            };
                        });

                        orderInput.value = JSON.stringify(photoOrderData);
                    };

                }
            }

            function renderPhotos() {

                preview.innerHTML = "";

                savedPhotos.forEach(function (photo, index) {
                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";
                    item.dataset.photoId = String(photo.id);

                    const box = document.createElement("div");

                    box.className = "nikki-photo-box";

                    const img = document.createElement("img");
                    img.src = photo.url;
                    img.alt = "保存済み画像" + (index + 1);

                    box.appendChild(img);

                    box.addEventListener("click", function () {
                        const displayedPhotos = Array.from(
                            preview.querySelectorAll(".nikki-photo-item")
                        ).filter(function (item) {
                            return item.querySelector("img") !== null;
                        });

                        if (displayedPhotos[0] !== item) {
                            return;
                        }

                        editingIndex = index;
                        editingSavedIndex = null;
                        input.click();
                    });

                    const remove = document.createElement("button");
                    remove.type = "button";
                    remove.className = "nikki-photo-remove";
                    remove.textContent = "×";

                    remove.addEventListener("click", function () {
                        if (!confirm("この写真を削除しますか？")) {
                            return;
                        }

                        removedPhotoIds.push(photo.id);
                        savedPhotos.splice(index, 1);

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

                photos
                    .map(function (file, index) {
                        return { file: file, index: index };
                    })
                    .sort(function (a, b) {
                        const aPosition = Number.isInteger(a.file.oshiDisplayPosition)
                            ? a.file.oshiDisplayPosition
                            : Infinity;
                        const bPosition = Number.isInteger(b.file.oshiDisplayPosition)
                            ? b.file.oshiDisplayPosition
                            : Infinity;

                        return aPosition - bPosition;
                    })
                    .forEach(function ({ file, index }) {

                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";
                    item.dataset.newPhotoIndex = String(index);

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
                        const displayedPhotos = Array.from(
                            preview.querySelectorAll(".nikki-photo-item")
                        ).filter(function (item) {
                            return item.querySelector("img") !== null;
                        });

                        if (displayedPhotos[0] !== item) {
                            return;
                        }

                        editingSavedIndex = index;
                        editingIndex = null;
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

                    const photoNumber = savedPhotos.length + index + 1;

                    label.textContent = photoNumber === 1
                        ? "画像1（サムネ）"
                        : "画像" + photoNumber;

                    item.appendChild(box);
                    item.appendChild(remove);
                    item.appendChild(label);

                    preview.appendChild(item);

                });

                const positionedPhotos = Array.from(
                    preview.querySelectorAll(".nikki-photo-item")
                ).filter(function (item) {
                    return item.dataset.newPhotoIndex !== undefined;
                }).filter(function (item) {
                    const index = Number(item.dataset.newPhotoIndex);
                    return Number.isInteger(photos[index].oshiDisplayPosition);
                }).sort(function (a, b) {
                    const aIndex = Number(a.dataset.newPhotoIndex);
                    const bIndex = Number(b.dataset.newPhotoIndex);

                    return photos[aIndex].oshiDisplayPosition -
                           photos[bIndex].oshiDisplayPosition;
                });

                positionedPhotos.forEach(function (item) {
                    const index = Number(item.dataset.newPhotoIndex);
                    const position = photos[index].oshiDisplayPosition;

                    const items = Array.from(
                        preview.querySelectorAll(".nikki-photo-item")
                    ).filter(function (element) {
                        return element.querySelector("img") !== null;
                    });

                    const target = items[position];

                    if (target && target !== item) {
                        preview.insertBefore(item, target);
                    }
                });

                if (savedPhotos.length + photos.length < 10) {

                    
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
                        editingSavedIndex = null;
                        input.click();
                    });

                    item.appendChild(add);
                    preview.appendChild(item);
                }

                const photoItems = Array.from(
                    preview.querySelectorAll(".nikki-photo-item")
                ).filter(function (item) {
                    return item.querySelector("img") !== null;
                });

                photoItems.forEach(function (item, index) {
                    const label = item.querySelector("p");

                    if (label) {
                        label.textContent = index === 0
                            ? "画像1（サムネ）"
                            : "画像" + (index + 1);
                    }

                    item.dataset.photoOrder = String(index + 1);
                });
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

                if (editingSavedIndex !== null) {
                    if (valid.length > 0) {
                    
                        const oldPhoto = savedPhotos[editingSavedIndex];

                        const currentItems = Array.from(
                            preview.querySelectorAll(".nikki-photo-item")
                        ).filter(function (item) {
                            return item.querySelector("img") !== null;
                        });

                        const displayPosition = currentItems.findIndex(
                            function (item) {
                                return item.dataset.photoId === String(oldPhoto.id);
                            }
                        );

                        removedPhotoIds.push(oldPhoto.id);
                        savedPhotos.splice(editingSavedIndex, 1);

                        const replacementFile = valid[0];
                        replacementFile.oshiDisplayPosition = displayPosition;

                        photos.push(replacementFile);
                    }

                    editingSavedIndex = null;
                
                } else if (editingIndex !== null) {
                    if (valid.length > 0) {
                        const oldFile = photos[editingIndex];
                        const replacementFile = valid[0];

                        if (Number.isInteger(oldFile.oshiDisplayPosition)) {
                            replacementFile.oshiDisplayPosition =
                                oldFile.oshiDisplayPosition;
                        }

                        photos[editingIndex] = replacementFile;
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

            updateFiles();
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

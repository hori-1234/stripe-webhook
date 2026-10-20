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
            border: 6px solid #fffdf8;
            border-radius: 4px;
            box-sizing: border-box;
            background: #f2e8d9;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(94, 72, 44, 0.18);
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
            const input = document.getElementById("nikki-photo-input");
            const preview = document.getElementById("nikki-photo-preview");
            const count = document.getElementById("nikki-photo-count");
            const form = input.closest("form");
            const savedPhotosElement = document.getElementById("nikki-saved-photos");
            const savedPhotos = savedPhotosElement
                ? JSON.parse(savedPhotosElement.textContent)
                : [];

            // 表示順を唯一の配列で管理する（保存済み・新規を混在させる）。
            const entries = savedPhotos.map(function (photo) {
                return { kind: "saved", id: photo.id, url: photo.url };
            });
            const removedPhotoIds = new Set();
            let editingPosition = null;

            // picker は選択専用。input は送信専用。
            const picker = document.createElement("input");
            picker.type = "file";
            picker.accept = "image/*";
            picker.hidden = true;
            input.insertAdjacentElement("afterend", picker);

            const orderInput = document.createElement("input");
            orderInput.type = "hidden";
            orderInput.name = "photo_order_data";
            if (form) {
                form.querySelectorAll('input[name="photo_order_data"]').forEach(
                    function (element) { element.remove(); }
                );
                form.appendChild(orderInput);
            }

            function syncFiles() {
                const transfer = new DataTransfer();
                entries.forEach(function (entry) {
                    if (entry.kind === "new") {
                        transfer.items.add(entry.file);
                    }
                });
                input.files = transfer.files;
                count.textContent = "写真：" + entries.length + " / 10枚";

                if (form) {
                    form.querySelectorAll('input[name="remove_photo_ids"]').forEach(
                        function (element) { element.remove(); }
                    );
                    removedPhotoIds.forEach(function (id) {
                        const hidden = document.createElement("input");
                        hidden.type = "hidden";
                        hidden.name = "remove_photo_ids";
                        hidden.value = String(id);
                        form.appendChild(hidden);
                    });
                }
            }

            function syncOrder() {
                let newIndex = 0;
                const data = entries.map(function (entry, index) {
                    return {
                        photo_id: entry.kind === "saved" ? String(entry.id) : null,
                        new_photo_index: entry.kind === "new" ? newIndex++ : null,
                        photo_order: index + 1
                    };
                });
                orderInput.value = JSON.stringify(data);
            }

            function openPicker(position) {
                editingPosition = position;
                picker.multiple = position === null;
                picker.value = "";
                picker.click();
            }

            function renderPhotos() {
                preview.innerHTML = "";
                entries.forEach(function (entry, index) {
                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";
                    const box = document.createElement("div");
                    box.className = "nikki-photo-box";
                    const img = document.createElement("img");
                    if (entry.kind === "saved") {
                        img.src = entry.url;
                        img.alt = "保存済み画像" + (index + 1);
                    } else {
                        const url = URL.createObjectURL(entry.file);
                        img.src = url;
                        img.onload = function () { URL.revokeObjectURL(url); };
                        img.onerror = function () { URL.revokeObjectURL(url); };
                        img.alt = "新規画像" + (index + 1);
                    }
                    box.appendChild(img);
                    // 1枚目（サムネイル）のみ差し替え可能。
                    if (index === 0) {
                        box.addEventListener("click", function () {
                            openPicker(0);
                        });
                    } else {
                        box.style.cursor = "default";
                    }

                    const remove = document.createElement("button");
                    remove.type = "button";
                    remove.className = "nikki-photo-remove";
                    remove.textContent = "×";
                    remove.addEventListener("click", function () {
                        if (!confirm("この写真を削除しますか？")) {
                            return;
                        }
                        if (entry.kind === "saved") {
                            removedPhotoIds.add(entry.id);
                        }
                        entries.splice(index, 1);
                        syncFiles();
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

                if (entries.length < 10) {
                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";
                    const add = document.createElement("div");
                    add.className = "nikki-photo-box";
                    const plus = document.createElement("span");
                    plus.className = "nikki-photo-add";
                    plus.textContent = "+";
                    add.appendChild(plus);
                    add.addEventListener("click", function () {
                        openPicker(null);
                    });
                    item.appendChild(add);
                    preview.appendChild(item);
                }
                syncOrder();
            }

            picker.addEventListener("change", function () {
                const selected = Array.from(picker.files);
                picker.value = "";
                if (selected.length === 0) {
                    editingPosition = null;
                    return;
                }
                const valid = selected.filter(function (file) {
                    return file.type.startsWith("image/");
                });
                if (valid.length !== selected.length) {
                    alert("画像ファイルのみ選択できます");
                }

                if (editingPosition !== null) {
                    if (valid.length > 0 && editingPosition === 0 && entries.length > 0) {
                        const oldEntry = entries[0];
                        if (oldEntry.kind === "saved") {
                            removedPhotoIds.add(oldEntry.id);
                        }
                        entries[0] = { kind: "new", file: valid[0] };
                    }
                } else {
                    const remaining = 10 - entries.length;
                    if (valid.length > remaining) {
                        alert("写真は最大10枚までです");
                    }
                    valid.slice(0, remaining).forEach(function (file) {
                        entries.push({ kind: "new", file: file });
                    });
                }
                editingPosition = null;
                syncFiles();
                renderPhotos();
            });

            if (form) {
                form.addEventListener("submit", function () {
                    syncFiles();
                    syncOrder();
                });
            }
            syncFiles();
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

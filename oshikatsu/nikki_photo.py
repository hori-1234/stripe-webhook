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

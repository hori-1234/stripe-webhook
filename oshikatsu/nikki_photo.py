from markupsafe import Markup


def render_nikki_photo_form():
    html = """
    <div class="nikki-photo-section">
        <h3>写真（最大10枚）</h3>

        <input
            type="file"
            id="nikki-photo-input"
            name="photos"
            accept="image/*"
            multiple
        >

        <p id="nikki-photo-count">選択中：0 / 10枚</p>

        <div id="nikki-photo-preview"></div>
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

        .nikki-photo-item img {
            width: 100%;
            aspect-ratio: 1;
            object-fit: cover;
            border: 1px solid #ccc;
            border-radius: 5px;
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

            input.addEventListener("change", function () {
                preview.innerHTML = "";

                if (input.files.length > 10) {
                    alert("写真は最大10枚までです");
                    input.value = "";
                    count.textContent = "選択中：0 / 10枚";
                    return;
                }

                count.textContent =
                    "選択中：" + input.files.length + " / 10枚";

                Array.from(input.files).forEach(function (file, index) {
                    if (!file.type.startsWith("image/")) {
                        return;
                    }

                    const url = URL.createObjectURL(file);

                    const item = document.createElement("div");
                    item.className = "nikki-photo-item";

                    const img = document.createElement("img");
                    img.src = url;
                    img.onload = function () {
                        URL.revokeObjectURL(url);
                    };

                    const label = document.createElement("p");

                    label.textContent = index === 0
                        ? "（サムネ）"
                        : "写真 " + (index + 1);

                    item.appendChild(img);
                    item.appendChild(label);

                    preview.appendChild(item);
                });
            });
        });
    </script>
    """

    return Markup(html)

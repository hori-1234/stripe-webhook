from markupsafe import Markup, escape


def render_nikki_layout(diary=None, mode="input"):
    """
    推し活日記の共通レイアウト

    mode:
        input : 新規入力
        view  : 閲覧
        edit  : 編集

    diary:
        (日付, イベント名, 場所, 出演者, 日記本文)
    """

    if diary is None:
        diary = ("", "", "", "", "")

    event_date, event_name, place, performers, diary_text = (
        diary
    )

    def safe(value):
        return escape(
            "" if value is None else str(value)
        )

    if mode not in ("input", "view", "edit"):
        raise ValueError("不正な表示モードです")

    fields = [
        ("日付", "event_date", event_date),
        ("イベント名", "event_name", event_name),
        ("場所", "place", place),
        ("出演者", "performers", performers),
        ("日記", "diary_text", diary_text),
    ]

    html = '<div class="nikki-common-layout">'

    for label, name, value in fields:
        html += '<div class="nikki-field">'
        html += f'<label>{label}</label>'

        if mode == "view":
            html += (
                '<div class="nikki-value">'
                f'{safe(value)}'
                '</div>'
            )

        elif name == "event_date":
            html += (
                f'<input type="date" name="{name}" '
                f'value="{safe(value)}" required>'
            )

        elif name in ("performers", "diary_text"):
            html += (
                f'<textarea name="{name}">'
                f'{safe(value)}'
                '</textarea>'
            )

        else:
            html += (
                f'<input type="text" name="{name}" '
                f'value="{safe(value)}">'
            )

        html += '</div>'

    html += '</div>'

    html += """
    <style>
        .nikki-common-layout {
            width: 100%;
            max-width: 700px;
        }

        .nikki-field {
            margin-bottom: 16px;
        }

        .nikki-field label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .nikki-field input,
        .nikki-field textarea {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #aaa;
            border-radius: 5px;
            font-size: 16px;
        }

        .nikki-field textarea {
            min-height: 80px;
            resize: vertical;
        }

        .nikki-value {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #f8f8f8;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }
    </style>
    """

    return Markup(html)

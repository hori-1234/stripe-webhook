
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

    event_date, event_name, place, performers, diary_text = diary

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
        ("日記(本文)", "diary_text", diary_text),
    ]

    html = '<div class="nikki-common-layout">'

    if mode == "view":

        # 日付と場所を横並びに表示
        html += """
        <div class="nikki-view-date-place">
        """

        html += (
            '<div class="nikki-field">'
            '<label>日付</label>'
            f'<div class="nikki-value">{safe(event_date)}</div>'
            '</div>'
        )

        html += (
            '<div class="nikki-field">'
            '<label>場所</label>'
            f'<div class="nikki-value">{safe(place)}</div>'
            '</div>'
        )

        html += '</div>'

        # イベント名
        html += (
            '<div class="nikki-field">'
            '<label>イベント名</label>'
            f'<div class="nikki-value">{safe(event_name)}</div>'
            '</div>'
        )

        # 出演者
        html += (
            '<div class="nikki-field">'
            '<label>出演者</label>'
            f'<div class="nikki-value">{safe(performers)}</div>'
            '</div>'
        )

        # 日記本文の2段階トグル
        html += """
        <details class="nikki-diary-first">
            <summary aria-label="詳細を開く"></summary>

            <details class="nikki-diary-second">
                <summary>日記(本文)</summary>
        """

        html += (
            '<div class="nikki-value">'
            f'{safe(diary_text)}'
            '</div>'
        )

        html += """
            </details>
        </details>
        """

    else:

        # 新規登録・編集画面は従来どおり
        for label, name, value in fields:

            html += '<div class="nikki-field">'
            html += f'<label>{label}</label>'

            if name == "event_date":
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
            min-width: 0;
        }

        .nikki-field label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .nikki-field input,
        .nikki-field textarea {
            width: 90%;
            max-width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #aaa;
            border-radius: 5px;
            font-size: 16px;
        }

        .nikki-field input[type="date"] {
            width: 170px;
            max-width: 100%;
        }

        .nikki-field textarea {
            min-height: 80px;
            resize: vertical;
        }

        .nikki-field textarea[name="diary_text"] {
            min-height: 200px;
        }

        .nikki-field textarea[name="diary_text"] {
            min-height: 200px;
        }

        .nikki-value {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #f8f8f8;
            color: #222;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }

        /* 日付と場所を横並び */
        .nikki-view-date-place {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        /* 1段階目 */
        .nikki-diary-first > summary {
            cursor: pointer;
            list-style: none;
            text-align: center;
            padding: 10px;
            font-size: 20px;
            user-select: none;
        }

        .nikki-diary-first > summary::-webkit-details-marker {
            display: none;
        }

        .nikki-diary-first > summary::after {
            content: "▼";
        }

        .nikki-diary-first[open] > summary::after {
            content: "▲";
        }

        /* 2段階目 */
        .nikki-diary-second {
            margin-top: 10px;
        }

        .nikki-diary-second > summary {
            cursor: pointer;
            padding: 10px;
            font-weight: bold;
        }

        .nikki-diary-second .nikki-value {
            margin-top: 10px;
        }
    </style>
    """

    return Markup(html)

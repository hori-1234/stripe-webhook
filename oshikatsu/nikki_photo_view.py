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

    html += "</div>"

    return Markup(html)

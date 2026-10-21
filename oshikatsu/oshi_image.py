from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_BYTES = 300 * 1024
MAX_IMAGE_WIDTH = 1600
MAX_IMAGE_HEIGHT = 1600
MAX_UPLOAD_PIXELS = 25_000_000

Image.MAX_IMAGE_PIXELS = MAX_UPLOAD_PIXELS
warnings.filterwarnings("error", category=Image.DecompressionBombWarning)


def compress_oshi_image(image_bytes):
    if not image_bytes:
        raise ValueError("画像データがありません")
    
    try:
        with Image.open(BytesIO(image_bytes)) as original:
            if original.width * original.height > MAX_UPLOAD_PIXELS:
                raise ValueError("画像の解像度は2500万ピクセル以下にしてください")

            image = ImageOps.exif_transpose(original)
            image.load()
    except Image.DecompressionBombWarning:
        raise ValueError("画像の解像度は2500万ピクセル以下にしてください")
    except Image.DecompressionBombError:
        raise ValueError("画像の解像度は2500万ピクセル以下にしてください")
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError):
        raise ValueError("対応していない画像形式です")

    # 大きな画像は縦横比を維持して縮小
    image.thumbnail(
        (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT),
        Image.Resampling.LANCZOS
    )

    # WebPに対応する画像モードへ変換
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    # 品質を段階的に調整
    for quality in (85, 75, 65, 55, 45, 35, 25, 15):
        output = BytesIO()

        image.save(
            output,
            format="WEBP",
            quality=quality,
            method=6
        )

        compressed = output.getvalue()

        if len(compressed) <= MAX_IMAGE_BYTES:
            return compressed

    # 品質調整だけで収まらなければ画像サイズを縮小
    while image.width > 100 or image.height > 100:
        new_width = max(1, int(image.width * 0.8))
        new_height = max(1, int(image.height * 0.8))

        if (new_width, new_height) == image.size:
            break

        image = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

        output = BytesIO()
        image.save(
            output,
            format="WEBP",
            quality=65,
            method=6
        )

        compressed = output.getvalue()

        if len(compressed) <= MAX_IMAGE_BYTES:
            return compressed

    raise ValueError("画像を300KB以下に圧縮できませんでした")

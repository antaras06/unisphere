import os
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError

MAX_DIMENSION = 1400


class InvalidImage(ValueError):
    pass


def _extension_ok(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def save_listing_image(file_storage):
    """Validate and persist an uploaded image. Returns the stored filename.

    The image is re-encoded with Pillow, which strips any embedded payloads and
    normalises the format, so only genuine image data ever reaches the disk.
    """
    if not file_storage or not file_storage.filename:
        raise InvalidImage("No file selected.")
    if not _extension_ok(file_storage.filename):
        raise InvalidImage("Only JPG, PNG and WEBP images are allowed.")

    try:
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise InvalidImage(f"'{file_storage.filename}' is not a valid image.")

    if img.format not in {"JPEG", "PNG", "WEBP"}:
        raise InvalidImage("Only JPG, PNG and WEBP images are allowed.")

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    has_alpha = img.mode == "RGBA"
    ext = "png" if has_alpha else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if has_alpha:
        img.save(path, format="PNG", optimize=True)
    else:
        img.save(path, format="JPEG", quality=85, optimize=True)
    return filename


def delete_image_file(filename):
    if not filename:
        return
    safe = os.path.basename(filename)
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass

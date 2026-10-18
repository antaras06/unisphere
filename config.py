import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://unisphere:unisphere_dev_pw@localhost:3306/unisphere?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Relative paths are resolved against the project root so `UPLOAD_FOLDER=instance/uploads`
    # works from any working directory (Flask would otherwise resolve them against app/).
    UPLOAD_FOLDER = str((BASE_DIR / os.getenv("UPLOAD_FOLDER", "instance/uploads")).resolve())
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    MAX_IMAGES_PER_LISTING = int(os.getenv("MAX_IMAGES_PER_LISTING", "5"))
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    WTF_CSRF_TIME_LIMIT = None

    SOCKETIO_ASYNC_MODE = os.getenv("SOCKETIO_ASYNC_MODE") or None
    SOCKETIO_MESSAGE_QUEUE = os.getenv("SOCKETIO_MESSAGE_QUEUE") or None
    CHAT_POLL_INTERVAL_MS = int(os.getenv("CHAT_POLL_INTERVAL_MS", "8000"))

    DEFAULT_COLLEGE = os.getenv("DEFAULT_COLLEGE", "Ness Wadia College of Commerce, Pune")
    LISTINGS_PER_PAGE = 12


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)
    REMEMBER_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", True)


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "mysql+pymysql://unisphere:unisphere_dev_pw@localhost:3306/unisphere_test?charset=utf8mb4",
    )
    SOCKETIO_ASYNC_MODE = "threading"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

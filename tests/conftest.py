import io
import os
import tempfile

import pytest
from PIL import Image

os.environ.setdefault("FLASK_ENV", "testing")

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture(scope="session")
def app():
    upload_dir = tempfile.mkdtemp(prefix="unisphere-test-uploads-")
    os.environ["UPLOAD_FOLDER"] = upload_dir
    app = create_app("testing")
    app.config["UPLOAD_FOLDER"] = upload_dir
    with app.app_context():
        _db.drop_all()
        _db.create_all()
    yield app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(autouse=True)
def app_ctx(app):
    """Fresh app context per test (Flask-Login caches the user on ``g``), then wipe all rows."""
    with app.app_context():
        yield
        _db.session.remove()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        _db.session.remove()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(email="alice@example.com", first="Alice", last="Shah", password="Password123", **kw):
    user = User(first_name=first, last_name=last, email=email, course="B.COM", year="TY",
                college="Ness Wadia College of Commerce, Pune", **kw)
    user.set_password(password)
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def alice(app):
    return make_user()


@pytest.fixture
def bob(app):
    return make_user(email="bob@example.com", first="Bob", last="Mehta")


def login(client, email, password="Password123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def image_bytes(fmt="PNG", size=(300, 200), color=(17, 85, 255)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    buf.seek(0)
    return buf


def listing_payload(**overrides):
    data = {
        "title": "Financial Accounting textbook",
        "description": "TY B.COM Sem V book, light highlights only.",
        "price": "320",
        "category": "Textbooks",
        "condition": "Good",
        "college": "Ness Wadia College of Commerce, Pune",
        "location": "NWCC campus",
        "images": (image_bytes(), "book.png"),
    }
    data.update(overrides)
    return data

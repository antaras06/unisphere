from app.models import User
from tests.conftest import login


def test_register_login_logout(client, db):
    r = client.post("/register", data={
        "first_name": "Neha", "last_name": "Joshi", "email": "Neha@Example.com", "course": "BBA", "year": "SY",
        "college": "Ness Wadia College of Commerce, Pune", "password": "Secret123", "confirm_password": "Secret123",
    }, follow_redirects=True)
    assert r.status_code == 200
    user = User.query.filter_by(email="neha@example.com").one()
    assert user.password_hash != "Secret123" and user.check_password("Secret123")

    client.post("/logout")
    assert client.get("/profile").status_code == 302

    assert b"Welcome back" in login(client, "neha@example.com", "Secret123").data
    assert client.get("/profile").status_code == 200


def test_register_validation_errors(client, alice):
    r = client.post("/register", data={
        "first_name": "A", "last_name": "", "email": alice.email, "course": "", "year": "",
        "college": "", "password": "short", "confirm_password": "other",
    })
    assert r.status_code == 200
    body = r.data.decode()
    assert "already exists" in body
    assert "at least 8 characters" in body
    assert "Passwords must match" in body
    assert User.query.count() == 1


def test_login_wrong_password(client, alice):
    r = client.post("/login", data={"email": alice.email, "password": "nope"})
    assert r.status_code == 401
    assert b"Incorrect email or password" in r.data


def test_protected_routes_redirect(client):
    for path in ["/sell", "/favourites", "/messages", "/profile", "/my-listings"]:
        r = client.get(path)
        assert r.status_code == 302 and "/login" in r.headers["Location"], path


def test_edit_profile_and_change_password(client, alice):
    login(client, alice.email)
    r = client.post("/profile/edit", data={"first_name": "Alicia", "last_name": "Shah", "course": "BBA IB",
                                           "year": "FY", "college": "Some Other College", "phone": "", "bio": "hi"},
                    follow_redirects=True)
    assert b"Profile updated" in r.data
    db_user = User.query.get(alice.id)
    assert db_user.first_name == "Alicia" and db_user.college == "Some Other College"

    r = client.post("/profile/password", data={"current_password": "wrong", "new_password": "NewPass123",
                                               "confirm_password": "NewPass123"})
    assert b"Current password is incorrect" in r.data
    r = client.post("/profile/password", data={"current_password": "Password123", "new_password": "NewPass123",
                                               "confirm_password": "NewPass123"}, follow_redirects=True)
    assert b"Password updated" in r.data
    assert User.query.get(alice.id).check_password("NewPass123")


def test_public_profile(client, alice):
    r = client.get(f"/users/{alice.id}")
    assert r.status_code == 200 and b"Alice Shah" in r.data
    assert b"alice@example.com" not in r.data
    assert client.get("/users/9999").status_code == 404

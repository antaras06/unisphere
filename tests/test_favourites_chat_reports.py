from app.models import Conversation, Favourite, Message, Report
from tests.conftest import listing_payload, login


def make_listing(client, owner, **kw):
    login(client, owner.email)
    client.post("/sell", data=listing_payload(**kw), content_type="multipart/form-data")
    client.post("/logout")
    from app.models import Listing
    return Listing.query.order_by(Listing.id.desc()).first()


def test_favourites_toggle_and_no_duplicates(client, alice, bob):
    listing = make_listing(client, alice)
    login(client, bob.email)
    r = client.post(f"/favourites/{listing.id}/toggle", headers={"X-Requested-With": "fetch"})
    assert r.get_json()["saved"] is True
    assert Favourite.query.count() == 1
    assert listing.title.encode() in client.get("/favourites").data

    r = client.post(f"/favourites/{listing.id}/toggle", headers={"X-Requested-With": "fetch"})
    assert r.get_json()["saved"] is False
    assert Favourite.query.count() == 0
    assert b"No favourites yet" in client.get("/favourites").data

    # Unique constraint at DB level
    from app.extensions import db
    import pytest
    from sqlalchemy.exc import IntegrityError
    db.session.add(Favourite(user_id=bob.id, listing_id=listing.id))
    db.session.add(Favourite(user_id=bob.id, listing_id=listing.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_sold_badge_shows_on_favourites(client, alice, bob):
    listing = make_listing(client, alice)
    login(client, bob.email)
    client.post(f"/favourites/{listing.id}/toggle")
    client.post("/logout")
    login(client, alice.email)
    client.post(f"/listings/{listing.id}/status", data={"status": "sold"})
    client.post("/logout")
    login(client, bob.email)
    assert b"SOLD" in client.get("/favourites").data


def test_chat_flow_and_privacy(client, alice, bob, app):
    listing = make_listing(client, alice)
    from tests.conftest import make_user
    carol = make_user(email="carol@example.com", first="Carol", last="Iyer")

    # Seller cannot chat with themselves
    login(client, alice.email)
    r = client.post(f"/listings/{listing.id}/chat", follow_redirects=True)
    assert b"own listing" in r.data and Conversation.query.count() == 0
    client.post("/logout")

    # Buyer starts conversation with first message
    login(client, bob.email)
    r = client.post(f"/listings/{listing.id}/chat", data={"message": "Is this available?"})
    conv = Conversation.query.one()
    assert conv.buyer_id == bob.id and conv.seller_id == alice.id and conv.listing_id == listing.id
    assert r.headers["Location"].endswith(f"/messages/{conv.id}")
    # Starting again reuses the same conversation
    client.post(f"/listings/{listing.id}/chat")
    assert Conversation.query.count() == 1

    r = client.post(f"/api/conversations/{conv.id}/messages", json={"body": "Can we meet at 11?"})
    assert r.status_code == 201 and r.get_json()["message"]["sender_id"] == bob.id
    assert client.post(f"/api/conversations/{conv.id}/messages", json={"body": "   "}).status_code == 400
    assert Message.query.count() == 2
    client.post("/logout")

    # Seller sees unread badge, opens conversation -> marked read
    login(client, alice.email)
    inbox = client.get("/messages")
    assert b"Bob Mehta" in inbox.data and b"Can we meet at 11?" in inbox.data
    assert Message.query.filter_by(is_read=False).count() == 2
    page = client.get(f"/messages/{conv.id}")
    assert page.status_code == 200 and b"Is this available?" in page.data
    assert Message.query.filter_by(is_read=False).count() == 0
    r = client.post(f"/api/conversations/{conv.id}/messages", json={"body": "Yes! 11 works."})
    assert r.status_code == 201
    client.post("/logout")

    # History persists for buyer after re-login
    login(client, bob.email)
    page = client.get(f"/messages/{conv.id}")
    assert b"Yes! 11 works." in page.data
    data = client.get(f"/api/conversations/{conv.id}/messages").get_json()
    assert [m["body"] for m in data["messages"]] == ["Is this available?", "Can we meet at 11?", "Yes! 11 works."]
    client.post("/logout")

    # Outsider cannot read or write
    login(client, carol.email)
    assert client.get(f"/messages/{conv.id}").status_code == 403
    assert client.get(f"/api/conversations/{conv.id}/messages").status_code == 403
    assert client.post(f"/api/conversations/{conv.id}/messages", json={"body": "hi"}).status_code == 403
    assert client.get("/messages/99999").status_code == 404
    assert Message.query.count() == 3


def test_reports(client, alice, bob):
    listing = make_listing(client, alice)
    login(client, bob.email)
    r = client.post(f"/report/listing/{listing.id}", data={"reason": "Scam or fraud", "details": "Suspicious"},
                    follow_redirects=True)
    assert b"Thanks for the report" in r.data
    report = Report.query.one()
    assert report.reporter_id == bob.id and report.listing_id == listing.id and report.reported_user_id == alice.id
    # duplicate open report is not created
    client.post(f"/report/listing/{listing.id}", data={"reason": "Scam or fraud"})
    assert Report.query.count() == 1
    # admin page forbidden for non-admin
    assert client.get("/admin/reports").status_code == 403
    client.post("/logout")

    login(client, alice.email)
    r = client.post(f"/report/listing/{listing.id}", data={"reason": "Scam or fraud"}, follow_redirects=True)
    assert b"own listing" in r.data

    from app.extensions import db
    alice.is_admin = True
    db.session.commit()
    r = client.get("/admin/reports")
    assert r.status_code == 200 and b"Scam or fraud" in r.data
    client.post(f"/admin/reports/{report.id}/resolve")
    assert Report.query.get(report.id).status == "resolved"


def test_csrf_enforced_when_enabled(app, alice):
    app.config["WTF_CSRF_ENABLED"] = True
    try:
        c = app.test_client()
        r = c.post("/login", data={"email": alice.email, "password": "Password123"})
        assert r.status_code == 400
    finally:
        app.config["WTF_CSRF_ENABLED"] = False


def test_last_message_is_latest(client, alice, bob, db):
    from datetime import datetime, timedelta

    listing = make_listing(client, alice)
    conv = Conversation(listing=listing, buyer=bob, seller=alice)
    db.session.add(conv)
    base = datetime(2026, 1, 1, 10, 0)
    for i, body in enumerate(["first", "second", "third"]):
        db.session.add(Message(conversation=conv, sender=bob, body=body, created_at=base + timedelta(minutes=i)))
    db.session.commit()
    assert conv.last_message.body == "third"

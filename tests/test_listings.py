import io
import os

from app.models import Listing, ListingImage
from tests.conftest import image_bytes, listing_payload, login


def create_listing(client, **overrides):
    r = client.post("/sell", data=listing_payload(**overrides), content_type="multipart/form-data", follow_redirects=False)
    return r


def test_create_listing_with_image(client, alice, app):
    login(client, alice.email)
    r = create_listing(client)
    assert r.status_code == 302
    listing = Listing.query.one()
    assert listing.seller_id == alice.id and listing.status == "available"
    assert len(listing.images) == 1
    path = os.path.join(app.config["UPLOAD_FOLDER"], listing.images[0].filename)
    assert os.path.exists(path)
    r = client.get(f"/uploads/{listing.images[0].filename}")
    assert r.status_code == 200 and r.mimetype.startswith("image/")
    detail = client.get(f"/listings/{listing.id}")
    assert detail.status_code == 200 and b"Financial Accounting textbook" in detail.data


def test_create_requires_image_and_valid_fields(client, alice):
    login(client, alice.email)
    r = client.post("/sell", data=listing_payload(images=(io.BytesIO(b""), ""), price="-5", title="ab"),
                    content_type="multipart/form-data")
    assert r.status_code == 400
    body = r.data.decode()
    assert "at least one product image" in body or "Price must be" in body
    assert Listing.query.count() == 0


def test_rejects_fake_image(client, alice):
    login(client, alice.email)
    r = client.post("/sell", data=listing_payload(images=(io.BytesIO(b"<?php echo 1; ?>"), "evil.png")),
                    content_type="multipart/form-data")
    assert r.status_code == 400
    assert b"not a valid image" in r.data
    assert Listing.query.count() == 0 and ListingImage.query.count() == 0


def test_rejects_disallowed_extension(client, alice):
    login(client, alice.email)
    r = client.post("/sell", data=listing_payload(images=(image_bytes("GIF"), "anim.gif")), content_type="multipart/form-data")
    assert r.status_code == 400
    assert Listing.query.count() == 0


def test_owner_can_edit_delete_and_toggle_sold(client, alice, app):
    login(client, alice.email)
    create_listing(client)
    listing = Listing.query.one()
    r = client.post(f"/listings/{listing.id}/edit", data=listing_payload(title="Updated title", price="299",
                                                                       images=(io.BytesIO(b""), "")),
                    content_type="multipart/form-data", follow_redirects=True)
    assert b"Listing updated" in r.data
    assert Listing.query.get(listing.id).title == "Updated title"

    r = client.post(f"/listings/{listing.id}/status", data={"status": "sold"}, follow_redirects=True)
    assert Listing.query.get(listing.id).status == "sold"
    assert b"SOLD" in client.get(f"/listings/{listing.id}").data
    assert b"Updated title" not in client.get("/browse").data
    assert b"Updated title" in client.get("/browse?include_sold=1").data
    client.post(f"/listings/{listing.id}/status", data={"status": "available"})
    assert Listing.query.get(listing.id).status == "available"

    filename = listing.images[0].filename
    r = client.post(f"/listings/{listing.id}/delete", follow_redirects=True)
    assert b"Listing deleted" in r.data
    assert Listing.query.count() == 0
    assert not os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], filename))


def test_non_owner_cannot_modify(client, alice, bob):
    login(client, alice.email)
    create_listing(client)
    listing = Listing.query.one()
    client.post("/logout")
    login(client, bob.email)
    assert client.get(f"/listings/{listing.id}/edit").status_code == 403
    assert client.post(f"/listings/{listing.id}/edit", data=listing_payload(title="Hacked"),
                       content_type="multipart/form-data").status_code == 403
    assert client.post(f"/listings/{listing.id}/status", data={"status": "sold"}).status_code == 403
    assert client.post(f"/listings/{listing.id}/delete").status_code == 403
    assert Listing.query.get(listing.id).title != "Hacked" and Listing.query.count() == 1


def test_anonymous_cannot_create(client):
    r = client.post("/sell", data=listing_payload(), content_type="multipart/form-data")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert Listing.query.count() == 0


def test_search_filter_sort(client, alice):
    login(client, alice.email)
    create_listing(client, title="Casio FX-991 calculator", category="Calculators", condition="Good", price="650")
    create_listing(client, title="Cost Accounting notes", category="Notes", condition="Like New", price="150")
    create_listing(client, title="Wildcraft backpack", category="Bags", condition="Fair", price="850")

    assert b"Casio FX-991" in client.get("/browse?q=casio").data
    assert b"Wildcraft" not in client.get("/browse?q=casio").data
    body = client.get("/browse?category=Notes").data
    assert b"Cost Accounting notes" in body and b"Casio" not in body
    body = client.get("/browse?condition=Fair").data
    assert b"Wildcraft" in body and b"Casio" not in body
    body = client.get("/browse?min_price=200&max_price=700").data
    assert b"Casio" in body and b"Wildcraft" not in body and b"Cost Accounting" not in body

    body = client.get("/browse?sort=price_asc").data.decode()
    assert body.index("Cost Accounting notes") < body.index("Casio FX-991") < body.index("Wildcraft backpack")
    body = client.get("/browse?sort=price_desc").data.decode()
    assert body.index("Wildcraft backpack") < body.index("Casio FX-991") < body.index("Cost Accounting notes")

    body = client.get("/browse?q=nonexistentthing").data
    assert b"No listings match" in body

    # Garbage input is ignored, not an error
    assert client.get("/browse?min_price=abc&sort=bogus&page=-1").status_code == 200

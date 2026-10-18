"""Seed UniSphere with NWCC-focused demo users, listings, favourites, chats.

Run with:  flask seed            (keeps existing data, skips if demo users exist)
           flask seed --reset    (wipes all tables first)
Demo accounts all use the password: Password123
"""
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

from PIL import Image, ImageDraw, ImageFont

from app.extensions import db
from app.models import Conversation, Favourite, Listing, ListingImage, Message, Report, User

DEMO_PASSWORD = "Password123"
NWCC = "Ness Wadia College of Commerce, Pune"

USERS = [
    dict(first_name="Aarav", last_name="Sharma", email="aarav@demo.unisphere", course="B.COM", year="TY", bio="TY B.COM. Selling last year's books and notes. Usually on campus 10–4."),
    dict(first_name="Priya", last_name="Deshmukh", email="priya@demo.unisphere", course="BBA", year="SY", bio="SY BBA · stationery hoarder turned seller."),
    dict(first_name="Rohan", last_name="Kulkarni", email="rohan@demo.unisphere", course="BBA CA", year="TY", bio="BBA CA final year. Programming books and gadgets."),
    dict(first_name="Sneha", last_name="Patil", email="sneha@demo.unisphere", course="BBA IB", year="FY", bio="First-year BBA IB, looking for second-hand textbooks."),
    dict(first_name="Admin", last_name="UniSphere", email="admin@demo.unisphere", course="B.COM", year="TY", bio="Platform moderator.", is_admin=True),
]

# (title, description, price, category, condition, seller_idx, location, palette, label)
LISTINGS = [
    ("Financial Accounting – TY B.COM Sem V (Nirali Prakashan)", "Latest syllabus edition, all chapters intact. Light pencil highlights in the first three units only. Includes solved illustrations. Perfect for TY B.COM students starting Sem V.", 320, "Textbooks", "Good", 0, "NWCC campus, near canteen", ("#1155FF", "#eaf0ff"), "FA"),
    ("Business Economics – SY B.COM (Sheth Publishers)", "Clean copy, no markings. Bought new last year, used for one semester.", 260, "Textbooks", "Like New", 0, "Camp, Pune", ("#0d9488", "#ccfbf1"), "BE"),
    ("Cost & Works Accounting handwritten notes (TY B.COM)", "Complete handwritten notes covering the full TY syllabus — Marginal costing, Standard costing, Process costing with solved problems. Scored 78 using these.", 150, "Notes", "Good", 0, "NWCC library steps", ("#7c3aed", "#ede9fe"), "CWA"),
    ("Casio FX-991ES Plus scientific calculator", "Works perfectly, 2nd edition. Cover included. Allowed in SPPU exams. Selling as I've graduated.", 650, "Calculators", "Good", 2, "Pune Station area", ("#111111", "#f3f4f6"), "fx-991"),
    ("Casio MJ-12D desktop calculator", "12-digit desktop calculator, great for accounting practicals. Minor scratches on the back, keys all fine.", 280, "Calculators", "Fair", 1, "NWCC campus", ("#374151", "#e5e7eb"), "MJ-12D"),
    ("SPPU previous year question papers – SY BBA (2019–2024)", "Printed set of question papers for all SY BBA subjects, both semesters, 2019 to 2024. Spiral bound. Great for pattern analysis before exams.", 120, "Question Papers", "Good", 1, "NWCC campus", ("#b45309", "#fef3c7"), "PYQ"),
    ("TY B.COM previous year papers bundle (Sem V & VI)", "Photocopied set for Sem V and VI including Auditing, Business Regulatory Framework, Cost Accounting, Marketing Management.", 100, "Question Papers", "Fair", 0, "Camp, Pune", ("#b45309", "#fef3c7"), "PYQ"),
    ("Python Programming – BBA CA (Vision Publications)", "BBA CA Sem III Python textbook, like new. A few exercises done in pencil, easily erasable.", 240, "Textbooks", "Like New", 2, "NWCC campus", ("#1155FF", "#eaf0ff"), "PY"),
    ("Let Us C – Yashavant Kanetkar (16th ed.)", "The classic C reference. Spine is fine, pages clean. Ideal for BBA CA first-year.", 200, "Reference Books", "Good", 2, "Koregaon Park", ("#0369a1", "#e0f2fe"), "C"),
    ("Taxmann's Income Tax Ready Reckoner (AY 2024-25)", "Reference book for TY B.COM Taxation. Barely used, no markings.", 380, "Reference Books", "Like New", 0, "NWCC campus", ("#0369a1", "#e0f2fe"), "TAX"),
    ("Classmate long notebooks – pack of 6 (unused)", "Six brand-new 172-page long notebooks, single line. Bought extra at the start of the year.", 220, "Stationery", "New", 1, "NWCC campus", ("#16a34a", "#dcfce7"), "6×"),
    ("Geometry box + drawing set (Camlin)", "Camlin geometry box with compass, set squares, protractor. Used once for a presentation.", 90, "Stationery", "Like New", 3, "NWCC campus", ("#16a34a", "#dcfce7"), "Camlin"),
    ("Wildcraft 30L laptop backpack – navy", "Padded laptop sleeve, two main compartments, rain cover included. Zips work perfectly. Used for one year.", 850, "Bags", "Good", 2, "Kalyani Nagar", ("#1e3a8a", "#dbeafe"), "30L"),
    ("Skybags tote bag for college", "Lightweight tote with inner pocket. Great for carrying 2–3 books and a bottle.", 350, "Bags", "Like New", 1, "Camp, Pune", ("#9d174d", "#fce7f3"), "Tote"),
    ("Milton 1L steel water bottle", "Insulated bottle, keeps water cold for hours. No dents.", 300, "Hostel Essentials", "Good", 3, "Hostel block, Camp", ("#0f766e", "#ccfbf1"), "1L"),
    ("Study table lamp (LED, rechargeable)", "Foldable LED lamp with 3 brightness levels, USB charging. Works great for late-night study.", 450, "Hostel Essentials", "Like New", 3, "Hostel block, Camp", ("#ca8a04", "#fef9c3"), "LED"),
    ("Single mattress (3x6 ft) + bedsheet", "Foam mattress used for one academic year in the hostel. Clean, no stains. Pick-up only.", 900, "Hostel Essentials", "Fair", 2, "Hostel block, Camp", ("#78350f", "#fef3c7"), "3×6"),
    ("boAt Rockerz 450 Bluetooth headphones", "Over-ear, 15-hour battery. Light wear on ear cushions. Comes with charging cable.", 700, "Electronics", "Good", 2, "NWCC campus", ("#111111", "#f3f4f6"), "boAt"),
    ("Pen drive 64GB SanDisk", "Used for a semester to carry presentations. Formatted and working.", 350, "Electronics", "Good", 1, "NWCC campus", ("#dc2626", "#fee2e2"), "64GB"),
    ("Business Mathematics & Statistics – FY B.COM", "Sold within a day — kept as reference for the Sold state.", 210, "Textbooks", "Good", 0, "NWCC campus", ("#1155FF", "#eaf0ff"), "BMS"),
    ("Marketing Management notes – SY BBA", "Full semester notes with diagrams; already sold.", 120, "Notes", "Good", 1, "NWCC campus", ("#7c3aed", "#ede9fe"), "MM"),
]
SOLD_TITLES = {"Business Mathematics & Statistics – FY B.COM", "Marketing Management notes – SY BBA"}


def _font(size):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_image(upload_folder, label, palette, title, variant=0):
    """Generate a simple product placeholder image (no external URLs)."""
    import uuid

    fg, bg = palette
    w, h = 800, 600
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    margin = 60 + variant * 20
    d.rounded_rectangle((margin, margin, w - margin, h - margin), radius=28, fill=fg)
    font = _font(96 if len(label) <= 4 else 64)
    bbox = d.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1] - 20), label, fill="#ffffff", font=font)
    small = _font(22)
    sub = title[:38] + ("…" if len(title) > 38 else "")
    bbox = d.textbbox((0, 0), sub, font=small)
    d.text(((w - (bbox[2] - bbox[0])) / 2, h - margin - 60), sub, fill="#ffffff", font=small)
    name = f"seed_{uuid.uuid4().hex}.jpg"
    img.save(os.path.join(upload_folder, name), "JPEG", quality=85)
    return name


def run_seed(reset=False):
    from flask import current_app

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    if reset:
        for model in (Message, Conversation, Report, Favourite, ListingImage, Listing, User):
            db.session.query(model).delete()
        db.session.commit()
        for f in os.listdir(upload_folder):
            if f.startswith("seed_"):
                os.remove(os.path.join(upload_folder, f))
    elif User.query.filter_by(email=USERS[0]["email"]).first():
        print("Demo data already present; use --reset to recreate.")
        return

    random.seed(42)
    users = []
    for u in USERS:
        user = User(college=NWCC, **u)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        users.append(user)
    db.session.flush()

    listings = []
    now = datetime.utcnow()
    for i, (title, desc, price, cat, cond, seller_idx, loc, palette, label) in enumerate(LISTINGS):
        created = now - timedelta(days=random.randint(0, 20), hours=random.randint(0, 23))
        listing = Listing(
            seller=users[seller_idx],
            title=title,
            description=desc,
            price=Decimal(price),
            category=cat,
            condition=cond,
            college=NWCC,
            location=loc,
            created_at=created,
            updated_at=created,
        )
        if title in SOLD_TITLES:
            listing.status = "sold"
            listing.sold_at = created + timedelta(days=1)
        n_images = 1 if i % 3 else 2
        for v in range(n_images):
            listing.images.append(ListingImage(filename=make_image(upload_folder, label, palette, title, v), position=v))
        db.session.add(listing)
        listings.append(listing)
    db.session.flush()

    aarav, priya, rohan, sneha, _admin = users
    db.session.add_all(
        [
            Favourite(user=sneha, listing=listings[0]),
            Favourite(user=sneha, listing=listings[3]),
            Favourite(user=sneha, listing=listings[19]),
            Favourite(user=priya, listing=listings[12]),
            Favourite(user=rohan, listing=listings[0]),
        ]
    )

    def chat(buyer, listing, lines, start_days_ago):
        if buyer is listing.seller:
            buyer = next(u for u in users if u is not listing.seller)
        conv = Conversation(listing=listing, buyer=buyer, seller=listing.seller)
        db.session.add(conv)
        t = now - timedelta(days=start_days_ago, hours=3)
        for idx, (who, text) in enumerate(lines):
            sender = buyer if who == "b" else listing.seller
            t = t + timedelta(minutes=random.randint(2, 40))
            db.session.add(Message(conversation=conv, sender=sender, body=text, created_at=t, is_read=idx < len(lines) - 1))
        conv.created_at = t
        conv.updated_at = t

    chat(sneha, listings[0], [
        ("b", "Hi Aarav! Is the Financial Accounting book still available?"),
        ("s", "Yes it is! Light highlights in the first 3 units only."),
        ("b", "Great. Can we meet near the canteen tomorrow around 11?"),
        ("s", "Works for me. I'll bring it along 👍"),
    ], 2)
    chat(priya, listings[3], [
        ("b", "Hello, does the FX-991ES have the hard cover?"),
        ("s", "Yes, cover included. Battery is fine too."),
        ("b", "Would you take ₹600?"),
    ], 1)
    chat(rohan, listings[12 - 0], [
        ("b", "Is the backpack's rain cover still with it?"),
    ], 0)

    db.session.add(
        Report(reporter=next(u for u in users if u is not listings[16].seller), listing=listings[16], reported_user=listings[16].seller, reason="Misleading description or price", details="Photo doesn't match the description — says mattress but shows only a label.")
    )
    db.session.commit()
    print(f"Seeded {len(users)} users, {len(listings)} listings. Demo password: {DEMO_PASSWORD}")

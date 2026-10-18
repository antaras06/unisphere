from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    course = db.Column(db.String(30), nullable=False)
    year = db.Column(db.String(5), nullable=False)
    college = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    bio = db.Column(db.String(300))
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)

    listings = db.relationship("Listing", back_populates="seller", lazy="dynamic", cascade="all, delete-orphan")
    favourites = db.relationship("Favourite", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.is_active_account

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256:600000")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_favourited(self, listing_id):
        return db.session.query(
            Favourite.query.filter_by(user_id=self.id, listing_id=listing_id).exists()
        ).scalar()

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Listing(TimestampMixin, db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    condition = db.Column(db.String(20), nullable=False, index=True)
    college = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(120))
    status = db.Column(db.String(10), nullable=False, default="available", index=True)
    sold_at = db.Column(db.DateTime)

    seller = db.relationship("User", back_populates="listings")
    images = db.relationship(
        "ListingImage",
        back_populates="listing",
        order_by="ListingImage.position",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    favourites = db.relationship("Favourite", back_populates="listing", cascade="all, delete-orphan", lazy="dynamic")
    conversations = db.relationship("Conversation", back_populates="listing", cascade="all, delete-orphan", lazy="dynamic")

    __table_args__ = (
        Index("ix_listings_status_created", "status", "created_at"),
        Index("ix_listings_price", "price"),
        CheckConstraint("price >= 0", name="ck_listings_price_nonneg"),
    )

    @property
    def is_sold(self):
        return self.status == "sold"

    @property
    def cover_image(self):
        return self.images[0] if self.images else None

    def __repr__(self):
        return f"<Listing {self.id} {self.title!r}>"


class ListingImage(db.Model):
    __tablename__ = "listing_images"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    position = db.Column(db.SmallInteger, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    listing = db.relationship("Listing", back_populates="images")


class Favourite(db.Model):
    __tablename__ = "favourites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="favourites")
    listing = db.relationship("Listing", back_populates="favourites")

    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_favourite_user_listing"),)


class Conversation(TimestampMixin, db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    listing = db.relationship("Listing", back_populates="conversations")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])
    messages = db.relationship(
        "Message", back_populates="conversation", order_by="Message.created_at", cascade="all, delete-orphan", lazy="dynamic"
    )

    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_id", name="uq_conversation_listing_buyer"),
        CheckConstraint("buyer_id <> seller_id", name="ck_conversation_distinct_parties"),
    )

    def is_participant(self, user):
        return user.is_authenticated and user.id in (self.buyer_id, self.seller_id)

    def other_party(self, user):
        return self.seller if user.id == self.buyer_id else self.buyer

    @property
    def last_message(self):
        return self.messages.order_by(Message.created_at.desc(), Message.id.desc()).first()

    def unread_count_for(self, user):
        return self.messages.filter(Message.sender_id != user.id, Message.is_read.is_(False)).count()


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")
    sender = db.relationship("User")

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_conversation_unread", "conversation_id", "is_read"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.full_name,
            "body": self.body,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() + "Z",
        }


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="SET NULL"), index=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reason = db.Column(db.String(60), nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(10), nullable=False, default="open", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    listing = db.relationship("Listing")
    reported_user = db.relationship("User", foreign_keys=[reported_user_id])

    # MySQL forbids CHECK constraints on columns used in ON DELETE SET NULL
    # foreign keys, so "a report must target a listing or a user" is enforced
    # in the report routes instead.

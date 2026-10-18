from datetime import datetime

from sqlalchemy import or_

from ..extensions import db
from ..models import Conversation, Message


def unread_count_for(user):
    return (
        db.session.query(db.func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            or_(Conversation.buyer_id == user.id, Conversation.seller_id == user.id),
            Message.sender_id != user.id,
            Message.is_read.is_(False),
        )
        .scalar()
        or 0
    )


def conversations_for(user):
    return (
        Conversation.query.filter(or_(Conversation.buyer_id == user.id, Conversation.seller_id == user.id))
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def mark_read(conversation, user):
    updated = (
        Message.query.filter(
            Message.conversation_id == conversation.id,
            Message.sender_id != user.id,
            Message.is_read.is_(False),
        ).update({"is_read": True}, synchronize_session=False)
    )
    if updated:
        db.session.commit()
    return updated


def add_message(conversation, sender, body):
    body = (body or "").strip()
    if not body:
        raise ValueError("Message cannot be empty.")
    if len(body) > 2000:
        raise ValueError("Message is too long (max 2000 characters).")
    message = Message(conversation=conversation, sender=sender, body=body)
    conversation.updated_at = datetime.utcnow()
    db.session.add(message)
    db.session.commit()
    return message

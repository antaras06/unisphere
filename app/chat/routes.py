from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db, socketio
from ..models import Conversation, Listing, Message
from .services import add_message, conversations_for, mark_read

chat_bp = Blueprint("chat", __name__)


def _get_conversation_or_abort(conversation_id):
    conversation = db.session.get(Conversation, conversation_id)
    if conversation is None:
        abort(404)
    if not conversation.is_participant(current_user):
        abort(403)
    return conversation


@chat_bp.route("/messages")
@login_required
def inbox():
    conversations = conversations_for(current_user)
    items = []
    for c in conversations:
        items.append(
            {
                "conversation": c,
                "other": c.other_party(current_user),
                "last": c.last_message,
                "unread": c.unread_count_for(current_user),
            }
        )
    return render_template("chat/inbox.html", items=items)


@chat_bp.route("/listings/<int:listing_id>/chat", methods=["POST"])
@login_required
def start(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    if listing.seller_id == current_user.id:
        flash("You can't start a chat about your own listing.", "warning")
        return redirect(url_for("listings.detail", listing_id=listing.id))
    conversation = Conversation.query.filter_by(listing_id=listing.id, buyer_id=current_user.id).first()
    if conversation is None:
        conversation = Conversation(listing=listing, buyer_id=current_user.id, seller_id=listing.seller_id)
        db.session.add(conversation)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            conversation = Conversation.query.filter_by(listing_id=listing.id, buyer_id=current_user.id).first()
    first_message = (request.form.get("message") or "").strip()
    if first_message:
        try:
            msg = add_message(conversation, current_user, first_message)
            socketio.emit("new_message", msg.to_dict(), to=f"conversation_{conversation.id}")
        except ValueError as e:
            flash(str(e), "danger")
    return redirect(url_for("chat.conversation", conversation_id=conversation.id))


@chat_bp.route("/messages/<int:conversation_id>")
@login_required
def conversation(conversation_id):
    conversation = _get_conversation_or_abort(conversation_id)
    mark_read(conversation, current_user)
    messages = conversation.messages.order_by(Message.created_at.asc(), Message.id.asc()).all()
    other = conversation.other_party(current_user)
    sidebar = conversations_for(current_user)
    return render_template(
        "chat/conversation.html",
        conversation=conversation,
        messages=messages,
        other=other,
        sidebar=sidebar,
    )


@chat_bp.route("/api/conversations/<int:conversation_id>/messages", methods=["GET"])
@login_required
def api_messages(conversation_id):
    conversation = _get_conversation_or_abort(conversation_id)
    after = request.args.get("after", 0, type=int)
    query = conversation.messages
    if after:
        query = query.filter(Message.id > after)
    messages = query.order_by(Message.created_at.asc(), Message.id.asc()).all()
    mark_read(conversation, current_user)
    return jsonify(messages=[m.to_dict() for m in messages])


@chat_bp.route("/api/conversations/<int:conversation_id>/messages", methods=["POST"])
@login_required
def api_send(conversation_id):
    conversation = _get_conversation_or_abort(conversation_id)
    payload = request.get_json(silent=True) or {}
    body = payload.get("body") if isinstance(payload, dict) else None
    if body is None:
        body = request.form.get("body")
    try:
        message = add_message(conversation, current_user, body)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    data = message.to_dict()
    socketio.emit("new_message", data, to=f"conversation_{conversation.id}")
    other = conversation.other_party(current_user)
    socketio.emit(
        "inbox_update",
        {"conversation_id": conversation.id, "preview": data["body"][:80], "sender_name": data["sender_name"]},
        to=f"user_{other.id}",
    )
    return jsonify(message=data), 201


@chat_bp.route("/messages/<int:conversation_id>/send", methods=["POST"])
@login_required
def send_fallback(conversation_id):
    """Plain-form fallback used when JavaScript is unavailable."""
    conversation = _get_conversation_or_abort(conversation_id)
    try:
        message = add_message(conversation, current_user, request.form.get("body"))
        socketio.emit("new_message", message.to_dict(), to=f"conversation_{conversation.id}")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("chat.conversation", conversation_id=conversation.id))

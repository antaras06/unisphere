from flask import request
from flask_login import current_user
from flask_socketio import disconnect, emit, join_room, leave_room

from ..extensions import db, socketio
from ..models import Conversation
from .services import add_message, mark_read


def _participant_conversation(conversation_id):
    if not current_user.is_authenticated:
        return None
    try:
        conversation = db.session.get(Conversation, int(conversation_id))
    except (TypeError, ValueError):
        return None
    if conversation is None or not conversation.is_participant(current_user):
        return None
    return conversation


@socketio.on("connect")
def on_connect():
    if not current_user.is_authenticated:
        disconnect()
        return False
    join_room(f"user_{current_user.id}")


@socketio.on("join_conversation")
def on_join(data):
    conversation = _participant_conversation((data or {}).get("conversation_id"))
    if conversation is None:
        emit("error", {"error": "Not allowed."})
        return
    join_room(f"conversation_{conversation.id}")
    mark_read(conversation, current_user)
    emit("joined", {"conversation_id": conversation.id})


@socketio.on("leave_conversation")
def on_leave(data):
    conversation = _participant_conversation((data or {}).get("conversation_id"))
    if conversation is not None:
        leave_room(f"conversation_{conversation.id}")


@socketio.on("send_message")
def on_send(data):
    conversation = _participant_conversation((data or {}).get("conversation_id"))
    if conversation is None:
        emit("error", {"error": "Not allowed."})
        return
    try:
        message = add_message(conversation, current_user, (data or {}).get("body"))
    except ValueError as e:
        emit("error", {"error": str(e)})
        return
    payload = message.to_dict()
    emit("new_message", payload, to=f"conversation_{conversation.id}")
    other = conversation.other_party(current_user)
    emit(
        "inbox_update",
        {"conversation_id": conversation.id, "preview": payload["body"][:80], "sender_name": payload["sender_name"]},
        to=f"user_{other.id}",
    )


@socketio.on("typing")
def on_typing(data):
    conversation = _participant_conversation((data or {}).get("conversation_id"))
    if conversation is None:
        return
    emit(
        "typing",
        {"conversation_id": conversation.id, "user_id": current_user.id, "name": current_user.first_name},
        to=f"conversation_{conversation.id}",
        include_self=False,
    )


@socketio.on("disconnect")
def on_disconnect():
    _ = request.sid

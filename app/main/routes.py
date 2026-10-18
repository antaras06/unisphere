import os

from flask import Blueprint, abort, current_app, render_template, send_from_directory
from sqlalchemy import func

from ..constants import CATEGORIES
from ..extensions import db
from ..models import Listing

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    latest = (
        Listing.query.filter_by(status="available").order_by(Listing.created_at.desc()).limit(8).all()
    )
    counts = dict(
        db.session.query(Listing.category, func.count(Listing.id))
        .filter(Listing.status == "available")
        .group_by(Listing.category)
        .all()
    )
    category_counts = [(c, counts.get(c, 0)) for c in CATEGORIES]
    total_available = sum(counts.values())
    return render_template(
        "index.html", latest=latest, category_counts=category_counts, total_available=total_available
    )


@main_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    safe = os.path.basename(filename)
    if safe != filename:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], safe, max_age=60 * 60 * 24 * 7)


@main_bp.route("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return {"status": "ok"}

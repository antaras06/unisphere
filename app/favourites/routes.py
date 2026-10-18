from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Favourite, Listing

favourites_bp = Blueprint("favourites", __name__)


def _wants_json():
    return request.headers.get("X-Requested-With") == "fetch" or request.accept_mimetypes.best == "application/json"


@favourites_bp.route("/favourites")
@login_required
def index():
    favourites = (
        Favourite.query.filter_by(user_id=current_user.id)
        .join(Listing)
        .order_by(Favourite.created_at.desc())
        .all()
    )
    return render_template("favourites/index.html", favourites=favourites)


@favourites_bp.route("/favourites/<int:listing_id>/toggle", methods=["POST"])
@login_required
def toggle(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    existing = Favourite.query.filter_by(user_id=current_user.id, listing_id=listing.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        saved = False
        msg = "Removed from favourites."
    else:
        db.session.add(Favourite(user_id=current_user.id, listing_id=listing.id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        saved = True
        msg = "Saved to favourites."
    if _wants_json():
        count = Favourite.query.filter_by(user_id=current_user.id).count()
        return jsonify(saved=saved, message=msg, count=count)
    flash(msg, "success")
    return redirect(request.referrer or url_for("listings.detail", listing_id=listing.id))

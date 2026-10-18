from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Listing, Report, User
from .forms import ReportForm

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/report/listing/<int:listing_id>", methods=["GET", "POST"])
@login_required
def report_listing(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    if listing.seller_id == current_user.id:
        flash("You can't report your own listing.", "warning")
        return redirect(url_for("listings.detail", listing_id=listing.id))
    form = ReportForm()
    if form.validate_on_submit():
        already = Report.query.filter_by(reporter_id=current_user.id, listing_id=listing.id, status="open").first()
        if already:
            flash("You've already reported this listing. Our team will review it.", "info")
            return redirect(url_for("listings.detail", listing_id=listing.id))
        db.session.add(
            Report(
                reporter_id=current_user.id,
                listing_id=listing.id,
                reported_user_id=listing.seller_id,
                reason=form.reason.data,
                details=(form.details.data or "").strip() or None,
            )
        )
        db.session.commit()
        flash("Thanks for the report. We'll review this listing.", "success")
        return redirect(url_for("listings.detail", listing_id=listing.id))
    return render_template("reports/form.html", form=form, listing=listing, reported_user=None)


@reports_bp.route("/report/user/<int:user_id>", methods=["GET", "POST"])
@login_required
def report_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.id == current_user.id:
        flash("You can't report yourself.", "warning")
        return redirect(url_for("auth.profile"))
    form = ReportForm()
    if form.validate_on_submit():
        already = Report.query.filter_by(
            reporter_id=current_user.id, reported_user_id=user.id, listing_id=None, status="open"
        ).first()
        if already:
            flash("You've already reported this user.", "info")
            return redirect(url_for("auth.public_profile", user_id=user.id))
        db.session.add(
            Report(
                reporter_id=current_user.id,
                reported_user_id=user.id,
                reason=form.reason.data,
                details=(form.details.data or "").strip() or None,
            )
        )
        db.session.commit()
        flash("Thanks for the report. We'll review this account.", "success")
        return redirect(url_for("auth.public_profile", user_id=user.id))
    return render_template("reports/form.html", form=form, listing=None, reported_user=user)

from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Report

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/reports")
@admin_required
def reports():
    status = request.args.get("status", "open")
    query = Report.query
    if status in ("open", "resolved"):
        query = query.filter_by(status=status)
    else:
        status = "all"
    reports = query.order_by(Report.created_at.desc()).all()
    return render_template("admin/reports.html", reports=reports, status=status)


@admin_bp.route("/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def resolve(report_id):
    report = db.session.get(Report, report_id)
    if report is None:
        abort(404)
    report.status = "resolved" if report.status == "open" else "open"
    db.session.commit()
    flash("Report updated.", "success")
    return redirect(url_for("admin.reports", status=request.args.get("status", "open")))

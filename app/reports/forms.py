from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from ..constants import REPORT_REASONS


class ReportForm(FlaskForm):
    reason = SelectField("Reason", choices=[("", "Select a reason…")] + [(r, r) for r in REPORT_REASONS], validators=[DataRequired()])
    details = TextAreaField("Details (optional)", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Submit report")

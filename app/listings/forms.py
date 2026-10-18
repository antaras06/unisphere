from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from ..constants import CATEGORIES, CONDITIONS


def _choices(values):
    return [("", "Select…")] + [(v, v) for v in values]


class ListingForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(min=3, max=120)])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=10, max=4000)])
    price = DecimalField(
        "Price (₹)",
        places=2,
        validators=[DataRequired(message="Enter a valid price."), NumberRange(min=0, max=9999999, message="Price must be between ₹0 and ₹99,99,999.")],
    )
    category = SelectField("Category", choices=_choices(CATEGORIES), validators=[DataRequired()])
    condition = SelectField("Condition", choices=_choices(CONDITIONS), validators=[DataRequired()])
    college = StringField("College", validators=[DataRequired(), Length(min=3, max=150)])
    location = StringField("Pickup location / area", validators=[Optional(), Length(max=120)])
    images = MultipleFileField(
        "Product images",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Only JPG, PNG and WEBP images are allowed.")],
    )
    submit = SubmitField("Publish listing")

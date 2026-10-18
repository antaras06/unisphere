from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from ..constants import COURSES, YEARS
from ..models import User


def _choices(values):
    return [("", "Select…")] + [(v, v) for v in values]


class RegisterForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(min=2, max=60)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(min=1, max=60)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=255)])
    course = SelectField("Course", choices=_choices(COURSES), validators=[DataRequired()])
    year = SelectField("Academic year", choices=_choices(YEARS), validators=[DataRequired()])
    college = StringField("College", validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=128, message="Password must be at least 8 characters."),
            Regexp(r".*\d.*", message="Password must contain at least one number."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists. Try logging in.")


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me logged in")
    submit = SubmitField("Log in")


class ProfileForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(min=2, max=60)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(min=1, max=60)])
    course = SelectField("Course", choices=_choices(COURSES), validators=[DataRequired()])
    year = SelectField("Academic year", choices=_choices(YEARS), validators=[DataRequired()])
    college = StringField("College", validators=[DataRequired(), Length(min=3, max=150)])
    phone = StringField(
        "Phone (optional, shown only to chat partners)",
        validators=[Optional(), Regexp(r"^[0-9+\-\s]{8,20}$", message="Enter a valid phone number.")],
    )
    bio = TextAreaField("Short bio", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Save changes")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(),
            Length(min=8, max=128, message="Password must be at least 8 characters."),
            Regexp(r".*\d.*", message="Password must contain at least one number."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")]
    )
    submit = SubmitField("Update password")

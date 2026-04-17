from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DateTimeLocalField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    username = StringField("Benutzername", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Passwort", validators=[DataRequired()])
    submit = SubmitField("Anmelden")


class RoleForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Beschreibung", validators=[Optional()])
    submit = SubmitField("Speichern")


class MemberForm(FlaskForm):
    first_name = StringField("Vorname", validators=[DataRequired(), Length(max=120)])
    last_name = StringField("Nachname", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-Mail", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Telefon", validators=[Optional(), Length(max=64)])
    street = StringField("Straße", validators=[Optional(), Length(max=255)])
    zip_code = StringField("PLZ", validators=[Optional(), Length(max=20)])
    city = StringField("Ort", validators=[Optional(), Length(max=120)])
    join_date = DateField("Beitrittsdatum", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[("active", "Aktiv"), ("inactive", "Inaktiv")],
        validators=[DataRequired()],
    )
    role_id = SelectField("Rolle", coerce=int, validators=[Optional()])
    notes = TextAreaField("Notizen", validators=[Optional()])
    submit = SubmitField("Speichern")


class EventForm(FlaskForm):
    title = StringField("Titel", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Beschreibung", validators=[Optional()])
    location = StringField("Ort", validators=[Optional(), Length(max=255)])
    event_date = DateTimeLocalField("Datum", validators=[DataRequired()], format="%Y-%m-%dT%H:%M")
    submit = SubmitField("Speichern")

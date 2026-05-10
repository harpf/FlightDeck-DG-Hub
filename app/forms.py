from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, URL


class LoginForm(FlaskForm):
    username = StringField("Benutzername", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Passwort", validators=[DataRequired()])
    submit = SubmitField("Anmelden")


class RegisterForm(FlaskForm):
    username = StringField("Benutzername", validators=[DataRequired(), Length(max=80)])
    email = StringField("E-Mail", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Passwort", validators=[DataRequired(), Length(min=10, max=120)])
    privacy_consent = BooleanField("Ich akzeptiere die Datenschutzerklärung", validators=[DataRequired()])
    submit = SubmitField("Registrieren")


class ProductForm(FlaskForm):
    name = StringField("Produktname", validators=[DataRequired(), Length(max=255)])
    manufacturer = StringField("Hersteller", validators=[Optional(), Length(max=255)])
    category = SelectField("Kategorie", choices=[("Disc", "Disc"), ("Bag", "Bag"), ("Basket", "Basket"), ("Accessory", "Accessory")], validators=[DataRequired()])
    disc_type = StringField("Disc-Typ", validators=[Optional(), Length(max=80)])
    speed = IntegerField("Speed", validators=[Optional(), NumberRange(min=1, max=15)])
    glide = IntegerField("Glide", validators=[Optional(), NumberRange(min=1, max=8)])
    turn = IntegerField("Turn", validators=[Optional(), NumberRange(min=-6, max=2)])
    fade = IntegerField("Fade", validators=[Optional(), NumberRange(min=0, max=6)])
    diameter_cm = FloatField("Durchmesser (cm)", validators=[Optional(), NumberRange(min=10, max=40)])
    weight_range_g = StringField("Gewichtsbereich (g)", validators=[Optional(), Length(max=32)])
    plastic_type = StringField("Plastic", validators=[Optional(), Length(max=120)])
    stability = StringField("Stability", validators=[Optional(), Length(max=120)])
    description = TextAreaField("Beschreibung", validators=[Optional()])
    product_url = StringField("Produkt-Link", validators=[Optional(), URL(), Length(max=500)])
    submit = SubmitField("Speichern")


class ProductReviewForm(FlaskForm):
    rating = IntegerField("Bewertung (1-5)", validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField("Kommentar", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Bewertung speichern")


class SourceRequestForm(FlaskForm):
    source_url = StringField("Website-URL", validators=[DataRequired(), URL(), Length(max=500)])
    note = TextAreaField("Notiz", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Source anfragen")


class SourceRequestStatusForm(FlaskForm):
    status = SelectField("Status", choices=[("open", "Open"), ("approved", "Approved"), ("rejected", "Rejected")])
    submit = SubmitField("Status setzen")


class ApiTokenForm(FlaskForm):
    name = StringField("Token Name", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Token erstellen")

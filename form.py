from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField,EmailField, validators, Form, RadioField
from wtforms.validators import Length, Email, EqualTo, ValidationError, InputRequired
from password_validator import PasswordValidator


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])

    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    forename = StringField('Forename', validators=[InputRequired()], render_kw={'placeholder': 'Enter your forename'})
    familyname = StringField('Family name', validators=[InputRequired()], render_kw={'placeholder': 'Enter your family name'})
    mobile = StringField('Mobile', validators=[InputRequired()], render_kw={'placeholder': 'Enter your mobile number'})
    email = EmailField(validators=[InputRequired(), Email()], render_kw={'placeholder': 'Email'})
    password = PasswordField(validators=[InputRequired(), Length(min=6, max=20)], render_kw={'placeholder': 'Password'})
    confirm = PasswordField(validators=[InputRequired()], render_kw={'placeholder': 'Confirm Password'})
    accept_tos = BooleanField('I accept the terms and conditions', validators=[InputRequired()])
    submit = SubmitField('Register')

class ReportForm(FlaskForm):
    vulnerability = RadioField('Label', choices=[('value','Injection'),('value_two','Broken Authentication'),('value_three','Sensitive Data Exposure'),('value_four','XML External Entities'),('value_five','Cross Site Scripting'),('value_six','Broken Access Control'),('value_seven','Insecure Deserialisation'),('value_eight','Availability'),('value_nine','Integrity'),('value_10','Confidentiality'),('value_eleven','Other')], default='value')
    explanation = TextAreaField('Explanation of vulnerability - 250 characters max', validators=[InputRequired(), Length(min=1, max=250)])
    whyreport = TextAreaField('Why are you reporting this vulnerability? - 250 characters max', validators=[InputRequired(), Length(min=1, max=250)])
    domainip = TextAreaField('Domain name or IP address relating to the report', validators=[InputRequired(), Length(min=1, max=50)])
    submit = SubmitField('Submit Form')


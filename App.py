
from flask import Flask, request, render_template, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy

from form import LoginForm, RegistrationForm, ReportForm, MessageForm, UpdateDetailsForm, UpdatePasswordForm

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from werkzeug.security import check_password_hash, generate_password_hash

from datetime import datetime

from encrypt import encrypt_data_dict, decrypt_data

from cryptography.fernet import Fernet

app = Flask(__name__)  # create an instance of the Flask class

app.config['SECRET_KEY'] = '5c7d9fe414fc668876f91637635567c4'  # set the secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

# from classdef import User

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Define the routes for the app to display specific pages

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    surname_prefix = db.Column(db.String)
    surname = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    phone_number = db.Column(db.String)
    role = db.Column(db.String, default="User")
    is_deleted = db.Column(db.Boolean, default=False)
    enc_key = db.Column(db.String)

    userreports = db.relationship('Report', backref="user", lazy=True)
    usermessages = db.relationship('Message', backref="from_user", lazy=True)


class Report(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    report_content = db.Column(db.LargeBinary)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date_time = db.Column(db.DateTime, default=datetime.utcnow)

    reportmessages = db.relationship('Message', backref="report", lazy=True)


class Message(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.LargeBinary)
    from_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey("report.id"), nullable=False)
    date_time = db.Column(db.DateTime, default=datetime.utcnow)

    messagereports = db.relationship("Report", backref="messages")

    # messagereports = db.relationship('Report', backref="messages", lazy=True)


@login_manager.user_loader
def load_user(user_id):
    """Loads user as current_user.

    Args:
        user_id -- id of logged in user.
    """

    return User.query.get(int(user_id))


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    else:
        return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if (current_user.is_authenticated):
        return redirect(url_for('dashboard'))

    form = RegistrationForm()

    if form.is_submitted() and not form.validate():
        flash("Please fix the errors below and try again.", "danger")

    elif form.validate_on_submit():
        # access the data from fields in the form like this print(form.email)

        if User.query.filter_by(email=form.email.data).first():
            flash('This email is unavailable. Please use a different email.', "warning")
            return redirect('/register')

        user_enc_key = Fernet.generate_key()

        add_user = User(
            first_name=form.first_name.data,
            surname_prefix=form.surname_prefix.data,
            surname=form.surname.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data, 'sha256'),
            phone_number=form.phone_number.data,
            role="User",
            is_deleted=0,
            enc_key=user_enc_key.decode('utf-8')
        )

        db.session.add(add_user)
        db.session.commit()

        flash(f"Account for {form.email.data} successfully created", "success")
        return redirect(url_for('login'))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if (current_user.is_authenticated):
        print("Logged in")
        return redirect(url_for('dashboard'))
        # return redirect('/dashboard')

    form = LoginForm()
    if form.is_submitted() and not form.validate():
        flash("Please fix the errors below and try again.", "danger")

    elif form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if not user or not check_password_hash(user.password, form.password.data):
            flash("Login failed: Invalid/Unknown login credentials.", "danger")
            return redirect('/login')

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template("login.html", title="Login", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')


@app.route("/submitreport", methods=["GET", "POST"])
@login_required
def submitreport():
    form = ReportForm()

    if form.is_submitted() and not form.validate():
        flash("Please fix the errors below and try again.", "danger")

    elif form.validate_on_submit():

        data = {
            "vulnerability": form.vulnerability.data,
            "explanation": form.explanation.data,
            "whyreport": form.whyreport.data,
            "domainip": form.domainip.data
        }

        encrypted_data = encrypt_data_dict(data, current_user.enc_key)

        add_report = Report(
            report_content=encrypted_data,
            user_id=current_user.id,
            date_time=datetime.utcnow()
        )

        db.session.add(add_report)
        db.session.commit()

        # flash(f"Account for {form.email.data} successfully created", "success")
        # return redirect(url_for('login'))

        flash("Report Submission Successful", "success")
        return redirect(url_for('dashboard'))
    else:
        return render_template("report.html", title="Create CVD Report", form=form, mode="Create")


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "Admin":

        reports_encr = db.session.query(Report) \
            .order_by(Report.date_time.desc()).all()

    else:

        reports_encr = db.session.query(Report) \
            .where(current_user.id == Report.user_id) \
            .order_by(Report.date_time.desc()).all()

    reports = []
    for rep in reports_encr:
        content = decrypt_data(rep.report_content, rep.user.enc_key)
        content['vulnerability'] = " ".join(map(str.capitalize, content['vulnerability'].split("_")))
        other_fields = {
            "id": rep.id,
            "user_id": rep.user_id,
            "date_time": rep.date_time.strftime('%Y-%m-%d %H:%M'),
            "user_email": rep.user.email
        }
        other_fields.update(content)
        reports.append(other_fields)

    return render_template("dashboard.html", reports=reports, role=current_user.role)



@app.route("/messaging/<int:report_id>/<int:msg_id>", methods=["GET", "POST"])
@app.route("/messaging/<int:report_id>", methods=["GET", "POST"])
@login_required
def messaging(report_id, msg_id=None):
    report_encr = db.session.query(Report) \
        .where(report_id == Report.id) \
        .first()

    if not report_encr:
        return abort(404)

    # If the user isn't an admin and they aren't the one who submitted the report, deny
    if current_user.role != "Admin" and report_encr.user_id != current_user.id:
        return abort(403)

    #Get the anchor if one is present, which will point to a specific message
    anchor = None
    if msg_id:
        anchor = "#msg_%s" % msg_id

    content = decrypt_data(report_encr.report_content, report_encr.user.enc_key)
    content['vulnerability'] = " ".join(map(str.capitalize, content['vulnerability'].split("_")))
    report = {
        "id": report_encr.id,
        "user_id": report_encr.user_id,
        "user_email": report_encr.user.email,
        "date_time": report_encr.date_time.strftime('%Y-%m-%d %H:%M')
    }
    report.update(content)

    form = MessageForm()
    if form.is_submitted() and not form.validate():
        flash("Invalid message: unable to post message.", "danger")

    elif form.validate_on_submit():
        encrypted_data = encrypt_data_dict(form.message.data, report_encr.user.enc_key)

        add_msg = Message(
            message=encrypted_data,
            from_user_id=current_user.id,
            report_id=report_id,
            date_time=datetime.utcnow()
        )

        db.session.add(add_msg)
        db.session.commit()

        flash("Message posted successfully", 'success')
        #Doing this to get a fresh copy of the page; if user refreshes it won't keep posted the same message
        return redirect(url_for("messaging",report_id=report_id,msg_id=msg_id))

    # Now retrieving, decrypting and preparing messages for display

    msgs_encr = db.session.query(Message).where(report_id == Message.report_id) \
        .order_by(Message.id) \
        .all()

    msgs = []
    for msg_encr in msgs_encr:

        email_class = "bg-warning"
        if msg_encr.from_user.email == report_encr.user.email:
            email_class = "bg-primary"

        msg = {
            'message': decrypt_data(msg_encr.message, report_encr.user.enc_key),
            'id': msg_encr.id,
            # 'from_user_id': msg_encr.from_user_id,
            'from_user_email': msg_encr.from_user.email,
            'date_time': msg_encr.date_time,
            'email_class': email_class
        }
        msgs.append(msg)

    return render_template("messaging.html", report=report, form=form, msgs=msgs, anchor=anchor)


@app.route("/deletereport/<int:report_id>", methods=["POST"])
@login_required
def deletereport(report_id):
    if current_user.role != "Admin":
        return abort(403)

    report = Report.query.filter_by(id=report_id).first_or_404()

    Message.query.filter_by(report_id=report_id).delete()

    db.session.delete(report)

    db.session.commit()

    flash("Report successfully deleted", "success")

    return redirect(url_for("dashboard"))


@app.route("/account/<string:email>", methods=["GET", "POST"])
@login_required
def getaccount(email):
    # If the user is not an admin and is trying to access someone else's account, deny
    if current_user.email != email and current_user.role != "Admin":
        abort(403)

    user = User.query.filter_by(email=email).first_or_404()

    # reports

    user_reports_encr = db.session.query(Report) \
        .where(user.id == Report.user_id) \
        .all()

    user_reports = []

    for report_encr in user_reports_encr:
        content = decrypt_data(report_encr.report_content, report_encr.user.enc_key)
        content['vulnerability'] = " ".join(map(str.capitalize, content['vulnerability'].split("_")))
        report = {
            "id": report_encr.id,
            "user_id": report_encr.user_id,
            "user_email": report_encr.user.email,
            "date_time": report_encr.date_time.strftime('%Y-%m-%d at %Hh%M'),
            "vulnerability": content['vulnerability']
        }
        user_reports.append(report)

    # end reports

    # msgs

    msgs_encr = db.session.query(Message).where(user.id == Message.from_user_id) \
        .order_by(Message.id) \
        .all()

    msgs = []
    for msg_encr in msgs_encr:
        msg = {
            'id': msg_encr.id,
            'from_report_id': msg_encr.report.id,
            'message': decrypt_data(msg_encr.message, msg_encr.report.user.enc_key),
            'from_user_email': msg_encr.from_user.email,
            'date_time': msg_encr.date_time.strftime("%Y-%m-%d at %Hh%M")
        }
        msgs.append(msg)

    # end msgs

    update_details_form = UpdateDetailsForm()
    update_password_form = UpdatePasswordForm()

    if update_details_form.validate_on_submit() and 'update_details' in request.form:

        user.first_name = update_details_form.first_name.data
        user.surname_prefix = update_details_form.surname_prefix.data
        user.surname = update_details_form.surname.data
        user.phone_number = update_details_form.phone_number.data

        db.session.commit()
        flash("Account details have been successfully updated", "success")

    elif request.method == 'GET':

        update_details_form.first_name.data = user.first_name
        update_details_form.surname_prefix.data = user.surname_prefix
        update_details_form.surname.data = user.surname
        update_details_form.phone_number.data = user.phone_number

    if update_password_form.validate_on_submit() and 'update_password' in request.form:
        user.password = generate_password_hash(update_password_form.password.data, 'sha256')
        db.session.commit()
        flash("Password has been successfully updated", "success")

    return render_template("account.html", user=user, reports=user_reports, msgs=msgs, form_details=update_details_form,
                           form_password=update_password_form)


# @app.route("/account/<string:email>", methods=["GET", "POST"])
# @login_required
# def getaccount(email):
#     # If the user is not an admin and is trying to access someone else's account, deny
#     if current_user.email != email and current_user.role != "Admin":
#         abort(403)
#
#     user = User.query.filter_by(email=email).first_or_404()
#
#     # reports
#
#     user_reports_encr = db.session.query(Report) \
#         .where(user.id == Report.user_id) \
#         .all()

@app.route("/deletemessage/<int:msg_id>", methods=["POST"])
@login_required
def deletemessage(msg_id):
    msg_encr = Message.query.filter_by(id=msg_id).first_or_404()

    if current_user.role != "Admin" and current_user.id != msg_encr.from_user.id:
        return abort(403)

    msg_report_id = msg_encr.report.id

    db.session.delete(msg_encr)
    db.session.commit()

    flash("Message has been deleted", "success")

    return redirect(url_for("messaging", report_id=msg_report_id))


@app.route("/editreport/<int:report_id>", methods=["GET", "POST"])
@login_required
def editreport(report_id):

    report_encr = db.session.query(Report) \
        .where(report_id == Report.id) \
        .first()

    if not report_encr:
        return abort(404)

    # If the user isn't an admin and they aren't the one who submitted the report, deny
    if current_user.role != "Admin" and report_encr.user_id != current_user.id:
        return abort(403)

    form = ReportForm()

    if form.is_submitted() and not form.validate():
        flash("Please fix the errors below and try again.","danger")

    elif form.validate_on_submit():

        data = {
            "vulnerability": form.vulnerability.data,
            "explanation": form.explanation.data,
            "whyreport": form.whyreport.data,
            "domainip": form.domainip.data
        }

        encrypted_data = encrypt_data_dict(data, report_encr.user.enc_key)

        report_encr.report_content = encrypted_data
        db.session.commit()
        flash("The report has been successfully updated.", "success")

        return redirect(url_for('dashboard'))

    if not form.is_submitted():

        content = decrypt_data(report_encr.report_content, report_encr.user.enc_key)
        form.vulnerability.data = content['vulnerability']
        form.explanation.data = content['explanation']
        form.whyreport.data = content['whyreport']
        form.domainip.data = content['domainip']

    form.submit.label.text = "Update"

    return render_template("report.html", title="Edit CVD Report", form=form, mode="Edit")


@app.errorhandler(405)  # This creates a customise 405 error page to prevent information leakage
def page_not_found(e):
    return render_template("error.html"), 405


@app.errorhandler(404)  # This creates a customise 404 error page to prevent information leakage
def page_not_found(e):
    return render_template("error.html"), 404


@app.errorhandler(403)  # This creates a customise 403 error page to prevent information leakage
def internal_server_error(e):
    return render_template("error.html"), 403


@app.errorhandler(500)  # This creates a customise 500 error page to prevent information leakage
def internal_server_error(e):
    return render_template("error.html"), 500


# End of route definitions


if __name__ == "__main__":
    app.run(debug=True)

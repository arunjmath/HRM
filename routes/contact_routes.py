from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

contact_bp = Blueprint("contact", __name__)

# Mongo collection import
from app import contacts_col


@contact_bp.route("/contact-us", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        contact_data = {
            "name": request.form.get("name"),
            "email": request.form.get("email"),
            "phone": request.form.get("phone"),
            "company": request.form.get("company", ""),
            "service": request.form.get("service"),
            "message": request.form.get("message"),
            "status": "new",
            "created_at": datetime.now()
        }

        # Save in MongoDB
        contacts_col.insert_one(contact_data)

        # Gmail Config
        EMAIL_ADDRESS = "kpery669@gmail.com"
        EMAIL_PASSWORD = "cuyonfyvuemrcevm"

        # Email Body
        subject = f"New Contact Form - {contact_data['name']}"

        body = f"""
New Contact Form Submission

Name: {contact_data['name']}
Email: {contact_data['email']}
Phone: {contact_data['phone']}
Company: {contact_data['company']}
Service: {contact_data['service']}

Message:
{contact_data['message']}
"""

        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = EMAIL_ADDRESS
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

        except Exception as e:
            print("Mail Error:", e)

        flash("Thank you! Message sent successfully.", "success")
        return redirect(url_for("contact.contact"))

    return render_template("contact.html")
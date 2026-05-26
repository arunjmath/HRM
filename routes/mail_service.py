import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_contact_email(contact_data):

    EMAIL_ADDRESS = "aaravpeoplepartners@gmail.com"

    EMAIL_PASSWORD = "eysuxcrrktsctevc"
     

    subject = f"New Contact Form Submission - {contact_data['name']}"

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

        print("Email Sent Successfully")

    except Exception as e:

        print("Email Error:", e)
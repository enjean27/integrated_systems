import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

# Store OTP temporarily (pwede mo palitan ng database later)
otp_storage = {}

# 🔢 Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))


# 💾 Save OTP with expiration (5 minutes)
def save_otp(email, otp):
    expiry_time = datetime.now() + timedelta(minutes=5)
    otp_storage[email] = {
        "otp": otp,
        "expires": expiry_time
    }


# ✅ Verify OTP
def verify_otp(email, user_otp):
    if email in otp_storage:
        stored_otp = otp_storage[email]["otp"]
        expiry = otp_storage[email]["expires"]

        if datetime.now() > expiry:
            return False, "OTP expired"

        if user_otp == stored_otp:
            del otp_storage[email]
            return True, "OTP verified"

    return False, "Invalid OTP"


# 📩 Send OTP via Gmail
def send_otp_email(sender_email, app_password, receiver_email, otp):
    try:
        subject = "Your OTP Code"
        body = f"Your OTP code is: {otp}"

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email

        # Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        return True, "OTP sent successfully"

    except Exception as e:
        return False, str(e)
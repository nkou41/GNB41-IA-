import os
import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

def send_email(to, subject, text):
    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "nkougnarigo226@gmail.com")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "GNB41 IA")

    if not api_key:
        raise Exception("BREVO_API_KEY manquante")

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": text,
    }
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }
    response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=15)
    if response.status_code >= 300:
        raise Exception(f"Brevo error {response.status_code}: {response.text}")
    return response.json()

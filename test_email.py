import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]

response = resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": ["delivered@resend.dev"],
    "subject": "マイマケ テストメール",
    "text": "Resendからのテストメールです。"
})

print(response)

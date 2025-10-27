import imaplib
import email
from email.header import decode_header
import email.message
import re
from typing import List, Dict
import datetime


def clean_text(text):
    return " ".join(text.split()) if text else ""


def is_probably_ad(msg: email.message.Message) -> bool:
    subject, _ = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(errors="ignore")
    subject = subject.lower()
    ad_keywords = ["newsletter", "promotion", "discount", "sale", "buy now", "unsubscribe"]
    return any(kw in subject for kw in ad_keywords)


def extract_email_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")
    return ""


def fetch_all_emails(imap_server: str, username: str, password: str) -> List[Dict]:
    results = []
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        mail.select("inbox")

        # 搜尋所有最近一週的郵件
        date = (datetime.date.today() - datetime.timedelta(days=1.1)).strftime("%d-%b-%Y")
        status, data = mail.search(None, f'(SINCE "{date}")')
        email_ids = data[0].split()

        for eid in reversed(email_ids):  # 從新到舊讀
            status, msg_data = mail.fetch(eid, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    sender = msg.get("From")
                    subject, _ = decode_header(msg.get("Subject"))[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors="ignore")
                    date = msg.get("Date")
                    body = extract_email_text(msg)
                    is_ad = is_probably_ad(msg)
                    results.append({
                        "from": clean_text(sender),
                        "to": clean_text(msg.get("To")),
                        "subject": clean_text(subject),
                        "date": clean_text(date),
                        "body": clean_text(body),
                        "is_ad": is_ad,
                        "recipient_account": username  # 👈 新增這行
                    })
        mail.logout()
    except Exception as e:
        print(f"❌ 錯誤：{e}")
    return results

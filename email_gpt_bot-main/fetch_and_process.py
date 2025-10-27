# [第 1 行 ~ 第 83 行]
import json
from utils.email_fetcher import fetch_all_emails
from utils.gpt_summary import gpt_summarize_email
from utils.report_writer import write_markdown_report
from openai import OpenAI
from markdown_it import MarkdownIt
import yagmail
from datetime import date
import os

def load_config():
    # 先擷取環境變數原始值
    raw_gpt_key = os.environ.get("GPT_API_KEY", "")
    raw_from_email = os.environ.get("SEND_EMAIL_FROM_EMAIL", "")
    raw_from_password = os.environ.get("SEND_EMAIL_FROM_PASSWORD", "")
    raw_report_receivers = os.environ.get("REPORT_RECEIVERS", "")
    raw_email_accounts = os.environ.get("EMAIL_ACCOUNTS", "[]")

    # 印出環境變數（顯示部分敏感資訊避免洩漏）
    print("==== Debug: 環境變數讀取結果 ====")
    print("GPT_API_KEY (部分) =", raw_gpt_key[:3] + "***" if raw_gpt_key else "(空/None)")
    print("SEND_EMAIL_FROM_EMAIL =", raw_from_email if raw_from_email else "(空/None)")
    print("SEND_EMAIL_FROM_PASSWORD (部分) =", raw_from_password[:3] + "***" if raw_from_password else "(空/None)")
    print("REPORT_RECEIVERS (原始) =", raw_report_receivers if raw_report_receivers else "(空/None)")
    print("EMAIL_ACCOUNTS (原始) =", raw_email_accounts[:60] + "..." if len(raw_email_accounts) > 60 else raw_email_accounts)
    print("================================")

    # 進行 JSON 解析時，可以用 try-except 看有沒有異常
    try:
        parsed_email_accounts = json.loads(raw_email_accounts)
    except json.JSONDecodeError as e:
        print("❌ 解析 EMAIL_ACCOUNTS JSON 時發生錯誤：", e)
        parsed_email_accounts = []

    return {
        "gpt_api_key": raw_gpt_key,
        "send_email_from": {
            "email": raw_from_email,
            "password": raw_from_password
        },
        "report_receivers": raw_report_receivers.split(","),  # 以逗號切割
        "email_accounts": parsed_email_accounts
    }

def main():
    print("\n===== main() 開始 =====")
    config = load_config()

    # 顯示 load_config() 後的 config 結果（同樣做部分遮罩）
    print("\n==== Debug: config 內容 ====")
    print("gpt_api_key (部分) =", config["gpt_api_key"][:3] + "***" if config["gpt_api_key"] else "(空/None)")
    print("send_email_from.email =", config["send_email_from"]["email"] if config["send_email_from"]["email"] else "(空/None)")
    print("send_email_from.password (部分) =", config["send_email_from"]["password"][:3] + "***" if config["send_email_from"]["password"] else "(空/None)")
    print("report_receivers =", config["report_receivers"])
    print("email_accounts =", config["email_accounts"])
    print("=============================\n")

    all_emails = []
    summaries = []

    # GPT 用來摘要每封信
    client = OpenAI(api_key=config.get("gpt_api_key"))
    print("🔍 準備開始處理郵件，OpenAI Client 初始化完成。")

    debug_mode = False
    if debug_mode:
        with open("test_data.txt", "r", encoding="utf-8") as file:
            summaries = file.read().split("\n\n")
            print("📄 測試模式：讀取 test_data.txt 完成，摘要數量：", len(summaries))
    else:
        # 取得所有信件
        for account in config.get("email_accounts", []):
            print(f"➡️ 正在處理帳號: {account.get('username')} @ {account.get('imap_server')}")
            emails = fetch_all_emails(
                imap_server=account["imap_server"],
                username=account["username"],
                password=account["password"]
            )
            print(f"  找到 {len(emails)} 封郵件")
            all_emails.extend(emails)

        # 對所有信件做 GPT 摘要
        print(f"📧 總共收集到 {len(all_emails)} 封郵件，開始摘要...")
        for i, email_item in enumerate(all_emails, start=1):
            print(f"  - 處理第 {i} 封郵件，主旨：{email_item.get('subject')}")
            reply = gpt_summarize_email(client, email_item, model="gpt-4o-mini")
            print("--- GPT 回覆 ---")
            print(reply)
            print("---------------")
            summaries.append(reply)

    # 整理並產出 Markdown 報告
    print("📝 開始整合摘要並產出 Markdown 報告...")
    markdown_text = write_markdown_report(all_emails, summaries, api_key=config.get("gpt_api_key"))
    print("📝 Markdown 內容預覽（前 200 字）：\n", markdown_text[:200])

    # 移除 markdown 清單開頭 "- "
    markdown_text = '\n'.join(line[2:] if line.strip().startswith("- ") else line for line in markdown_text.splitlines())

    # 轉換成 HTML
    md = MarkdownIt()
    html_body = md.render(markdown_text)
    print("🌐 轉換後 HTML 預覽（前 200 字）：\n", html_body[:200])
    html_content = f"""
    <html>
      <body style="font-family:Arial, sans-serif; line-height:1.6; padding:16px;">
        {html_body}
      </body>
    </html>
    """

    # 寄件相關
    print("📧 準備寄信...")
    send_from = config["send_email_from"]
    email_user = send_from["email"]
    email_pass = send_from["password"]
    to_list = config.get("report_receivers", [email_user])

    print("📤 即將寄出 Email 給：", to_list)
    print("  ➡️ 寄件人帳號 (email_user) =", email_user if email_user else "(空/None)")
    print("  ➡️ 寄件人密碼 (email_pass) (部分) =", email_pass[:3] + "***" if email_pass else "(空/None)")

    # 初始化 Yagmail
    try:
        yag = yagmail.SMTP(user=email_user, password=email_pass)
        today = date.today().strftime("%Y-%m-%d")
        # 寄出 Email（明確宣告這是 HTML）
        yag.send(
            to=to_list,
            subject=f"📬 每日郵件摘要：{today}",
            contents=[html_content]  # 明確指定 HTML 格式
        )
        print("✅ 寄信成功")
        print("郵件內容預覽：", html_content[:300], "...")
    except Exception as e:
        print(f"❌ 寄信發生錯誤: {e}")

    print("===== main() 結束 =====")

if __name__ == "__main__":
    main()

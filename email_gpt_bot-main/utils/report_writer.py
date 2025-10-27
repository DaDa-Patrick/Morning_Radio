import os
from datetime import datetime
from pathlib import Path
from openai import OpenAI



def parse_gpt_reply(text):
    result = {"summary": "", "important": "", "need_reply": "", "category": ""}
    lines = text.strip().split("\n")
    for line in lines:
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()

            if any(k in key for k in ["摘要", "summary"]):
                result["summary"] = val
            elif any(k in key for k in ["重要", "importance"]):
                result["important"] = val
            elif any(k in key for k in ["回覆", "reply"]):
                result["need_reply"] = val
            elif any(k in key for k in ["分類", "category"]):
                result["category"] = val
    return result


def write_markdown_report(emails, summaries, output_dir="output", api_key=None):
    today = datetime.today().strftime("%Y-%m-%d")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    md_path = os.path.join(output_dir, f"{today}.md")

    client = OpenAI(api_key=api_key)
    print("🧾 summaries length:", len(summaries))
    print("🧾 First item of summaries:", summaries[0] if summaries else "空")
    print("🧾 Sending to GPT:\n", "\n\n".join(summaries)[:1000])  # 顯示前 1000 字

    try:
        final_response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一位專業郵件助理，請根據提供的信件摘要，整理出一篇像電子報般精美、結構良好且資訊濃縮的 Markdown 報告。\n\n"
                        "請依以下原則整理：\n"
                        "0. 報告開頭請以屬下身份向 Patrick 呈報，整體風格類似一份公司內部精美電子報。報告開頭需包含一段約 100 字左右的導言，文中可加入問候語（如「親愛的 Patrick」），並以正式但不失溫度的語氣呈現今日來信的整體趨勢與重點事項，強調重要通知與需要回覆的郵件。適度加入醒目的粗體字以增加視覺效果。\n"
                        "1. 報告標題：『📬 今日郵件摘要』。\n"
                        "2. 報告內文請依照以下區塊分類，並依重要性順序整理（如遇到重複主題的郵件請合併重點）：\n"
                        "   - **📩 需要回覆的郵件**：包含助教、會議、合作提案等必須回覆的訊息。\n"
                        "   - **✉️ 優先通知**：涉及學業、考試、校務、報名等重要事務的郵件，或有明確提醒必須注意的事項。\n"
                        "   - **📢 推廣與演講資訊**：與研討會、活動邀請或講座通知相關的郵件，但無需立即回覆。\n"
                        "   - **🗂 其他通知**：包括系統通知、帳戶提醒、消息公告等其他資訊，請依照重要程度排序。\n"
                        "3. 每封郵件的內容格式請統一為：\n"
                        "   - **主旨：** （可簡化）\n"
                        "   - **📬 收件信箱：** xxx@xxx.com\n"
                        "   - **濃縮摘要：** （簡明扼要，建議不超過 30 字）\n"
                        "   - **相關鏈結：** (若有再提供)\n"
                        "4. 請注意排版與視覺效果，分段清晰且避免冗長，務必提升報告的易讀性與吸引力。\n\n"
                        "請依下列模板撰寫報告：\n"
                        "## 今日摘要\n"
                        "（以上屬下口吻撰寫約 100 字的摘要，概述今日主要來信趨勢與重點任務，並強調重要通知與需要回覆的事項）\n\n"
                        "## 📩 需要回覆的郵件\n"
                        "- **主旨：** xxx  \n"
                        "  **📬 收件信箱：** xxx@xxx.com  \n"
                        "  **濃縮摘要：** xxx\n\n"
                        "## ✉️ 優先通知\n"
                        "- **主旨：** xxx  \n"
                        "  **📬 收件信箱：** xxx@xxx.com  \n"
                        "  **濃縮摘要：** xxx\n\n"
                        "## 📢 推廣與演講資訊\n"
                        "- **主旨：** xxx  \n"
                        "  **📬 收件信箱：** xxx@xxx.com  \n"
                        "  **濃縮摘要：** xxx\n\n"
                        "## 🗂 其他通知\n"
                        "- **主旨：** xxx  \n"
                        "  **📬 收件信箱：** xxx@xxx.com  \n"
                        "  **濃縮摘要：** xxx\n"
                        "---\n"
                        "（附上結語，謝謝閱讀，並提醒關注後續重點更新。）"
                    )
                },
                {
                    "role": "user",
                    "content": "以下是今天收到的信件摘要，每封信可能包含：主旨、來源信箱、摘要、是否需要回覆、是否為推銷、是否包含重要資訊、自由分類：\n\n" + "\n\n".join(summaries)
                }
            ],
            temperature=0.4,
            max_tokens=5000
        )
        report = final_response.choices[0].message.content
        print("📝 GPT 回傳內容前 300 字：", report[:300])
        print("📝 回傳內容是否為空：", "是空的" if not report.strip() else "✅ 有內容")
    except Exception as e:
        report = f"# 郵件整理失敗\n\n原因：{e}"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report if report.strip() else "# ⚠️ GPT 回傳內容為空")

    return report

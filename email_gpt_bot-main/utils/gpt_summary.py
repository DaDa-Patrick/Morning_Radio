def build_prompt(email_item):
    body = email_item["body"]
    if email_item["is_ad"]:
        return f"這是一封廣告信，請略過摘要，只回答如下格式：\n摘要：略過\n是否重要：否\n是否需要回覆：否\n分類：廣告"

    return f"請幫我閱讀以下電子郵件，並完成以下分析：\n" \
           f"1. 郵件詳情 \n" \
           f"2. 是否重要？（是/否）\n" \
           f"3. 是否需要回覆？（是/否）\n" \
           f"4. 是否為推銷或宣傳性質？（是/否）\n" \
           f"5. 分類（例如：工作、個人、廣告等）\n" \
           f"6. 相關鏈結：\n\n" \
           f"\n---\nFrom: {email_item['from']}\nTo: {email_item['recipient_account']}\nSubject: {email_item['subject']}\nDate: {email_item['date']}\n\n{body[:2000]}\n---"


def gpt_summarize_email(client, email_item, model="gpt-4o-mini"):
    prompt = build_prompt(email_item)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一位善於閱讀電子郵件並生成摘要與分類的助理。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=1000
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"GPT API 錯誤：{e}")
        return "摘要：失敗\n是否重要：未知\n是否需要回覆：未知\n分類：未知"

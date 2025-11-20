import feedparser
import google.generativeai as genai
import requests
import time
from datetime import datetime, timedelta
from time import mktime
import os

# گرفتن کلیدها از گاوصندوق گیت‌هاب
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# لیست سایت‌های خبری (میتونی بعدا تغییر بدی)
RSS_URLS = [
    "https://www.isna.ir/rss",
    "https://www.zoomit.ir/feed/",
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def summarize_with_ai(title, content, link):
    prompt = f"""
    تو ادمین خبری هستی. این خبر را بخوان:
    عنوان: {title}
    متن: {content}

    وظایف:
    1. یک خلاصه 2 تا 3 خطی جذاب به فارسی بنویس.
    2. لحن رسمی اما روان باشد.
    3. در آخر خلاصه، حتما بنویس: "منبع: کانال ما" (بدون لینک).
    4. هیچ لینکی در متن نباشد.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return None

def check_feeds():
    print("شروع بررسی اخبار...")
    # فقط خبرهای 30 دقیقه اخیر را چک میکنیم که تکراری نباشد
    time_threshold = datetime.now() - timedelta(minutes=30)
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    if pub_date > time_threshold:
                        print(f"خبر جدید: {entry.title}")
                        summary = summarize_with_ai(entry.title, entry.summary, entry.link)
                        
                        if summary:
                            final_text = f"🚨 **{entry.title}**\n\n{summary}\n\n🔗 [مشاهده خبر اصلی]({entry.link})"
                            send_to_telegram(final_text)
                            time.sleep(5)
        except Exception as e:
            print(f"خطا در خواندن فید {url}: {e}")

if __name__ == "__main__":
    check_feeds()

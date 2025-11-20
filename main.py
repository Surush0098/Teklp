import feedparser
import google.generativeai as genai
import requests
import time
from datetime import datetime, timedelta
from time import mktime
import os

# دریافت کلیدها
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# لیست سایت‌ها (فقط زومیت)
RSS_URLS = [
    "https://www.zoomit.ir/feed/",
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

def send_to_telegram(message, image_url=None):
    """ارسال پیام (عکس‌دار یا متنی) به تلگرام"""
    try:
        if image_url:
            # اگر عکس داشت، با متد sendPhoto میفرستیم
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            data = {
                "chat_id": CHANNEL_ID,
                "photo": image_url,
                "caption": message,
                "parse_mode": "Markdown"
            }
        else:
            # اگر عکس نداشت، با متد sendMessage میفرستیم
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                "chat_id": CHANNEL_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            
        response = requests.post(url, data=data)
        print(f"وضعیت ارسال: {response.status_code}")
    except Exception as e:
        print(f"خطا در ارسال به تلگرام: {e}")

def summarize_with_ai(title, content):
    prompt = f"""
    تو ادمین کانال تکنولوژی هستی.
    خبر: {title}
    متن: {content}

    وظایف:
    1. یک متن جذاب، کوتاه و مفید (حدود 3 خط) بنویس.
    2. اصلا لینک منبع نگذار.
    3. ایموجی مرتبط استفاده کن.
    4. در آخر متن فقط بنویس: 🆔 @Teklp
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return None

def check_feeds():
    print("بررسی اخبار جدید...")
    # بررسی اخبار 30 دقیقه اخیر
    time_threshold = datetime.now() - timedelta(minutes=30)
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    if pub_date > time_threshold:
                        print(f"خبر جدید: {entry.title}")
                        
                        # پیدا کردن عکس خبر
                        image_url = None
                        if 'links' in entry:
                            for link in entry.links:
                                if link.type == 'image/jpeg' or link.type == 'image/png':
                                    image_url = link.href
                                    break
                        # اگر در لینک‌ها نبود، گاهی در enclosures هست
                        if not image_url and hasattr(entry, 'enclosures'):
                             for enclosure in entry.enclosures:
                                if 'image' in enclosure.type:
                                    image_url = enclosure.href
                                    break

                        summary = summarize_with_ai(entry.title, entry.summary)
                        
                        if summary:
                            # تیتر را هم به متن اضافه میکنیم
                            final_text = f"🔥 **{entry.title}**\n\n{summary}"
                            send_to_telegram(final_text, image_url)
                            time.sleep(5)
        except Exception as e:
            print(f"خطا در فید: {e}")

if __name__ == "__main__":
    check_feeds()

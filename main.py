import feedparser
import google.generativeai as genai
import requests
import time
from datetime import datetime, timedelta
from time import mktime
import os
from bs4 import BeautifulSoup  # ابزار جدید برای استخراج عکس

# دریافت کلیدها
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# لیست سایت‌ها
RSS_URLS = [
    "https://www.zoomit.ir/feed/",
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

def send_to_telegram(message, image_url=None):
    """ارسال پیام به تلگرام (با عکس یا بدون عکس)"""
    try:
        if image_url:
            print(f"ارسال عکس: {image_url}")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            data = {
                "chat_id": CHANNEL_ID,
                "photo": image_url,
                "caption": message,
                "parse_mode": "Markdown"
            }
        else:
            print("ارسال بدون عکس")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                "chat_id": CHANNEL_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"خطای تلگرام: {response.text}")
    except Exception as e:
        print(f"خطا در ارسال: {e}")

def extract_image(entry):
    """تلاش برای پیدا کردن عکس به هر روش ممکن"""
    # روش ۱: بررسی مدیا کانتنت (استاندارد RSS)
    if 'media_content' in entry:
        for media in entry.media_content:
            if 'url' in media:
                return media['url']
    
    # روش ۲: بررسی لینک‌های ضمیمه
    if 'links' in entry:
        for link in entry.links:
            if link.type.startswith('image/'):
                return link.href
                
    # روش ۳: جستجو داخل متن خبر با BeautifulSoup (مخصوص زومیت)
    if 'summary' in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img_tag = soup.find('img')
        if img_tag and 'src' in img_tag.attrs:
            return img_tag['src']
            
    return None

def summarize_with_ai(title, content):
    prompt = f"""
    تو ادمین کانال تکنولوژی هستی.
    خبر: {title}
    متن: {content}

    وظایف:
    1. یک متن جذاب، کوتاه و مفید (حدود 3 خط) بنویس.
    2. لینک منبع نگذار.
    3. از ایموجی‌های تکنولوژی استفاده کن.
    4. خط آخر فقط بنویس: 🆔 @Teklp
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return None

def check_feeds():
    print("بررسی اخبار جدید...")
    time_threshold = datetime.now() - timedelta(minutes=30)
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    if pub_date > time_threshold:
                        print(f"خبر پیدا شد: {entry.title}")
                        
                        # استخراج عکس با تابع جدید
                        image_url = extract_image(entry)
                        
                        # خلاصه سازی
                        summary = summarize_with_ai(entry.title, entry.summary)
                        
                        if summary:
                            final_text = f"🔥 **{entry.title}**\n\n{summary}"
                            send_to_telegram(final_text, image_url)
                            time.sleep(5)
        except Exception as e:
            print(f"خطا در فید: {e}")

if __name__ == "__main__":
    check_feeds()

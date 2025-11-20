import feedparser
import google.generativeai as genai
import requests
import time
from datetime import datetime, timedelta
from time import mktime
import os
from bs4 import BeautifulSoup

# دریافت کلیدها
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

# منبع: فقط زومیت
RSS_URLS = [
    "https://www.zoomit.ir/feed/",
]

# مدل جدید با ظرفیت بالا (1000 درخواست در روز)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')

HISTORY_FILE = "history.txt"

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_to_history(link, title):
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{link}|{title}\n")
        os.system(f'git config --global user.name "News Bot"')
        os.system(f'git config --global user.email "bot@noreply.github.com"')
        os.system(f'git add {HISTORY_FILE}')
        os.system('git commit -m "Update history"')
        os.system('git push')
    except: pass

def check_is_duplicate_topic(new_title, history_lines):
    recent_titles = [line.split("|")[1] for line in history_lines[-50:] if len(line.split("|")) > 1]
    if not recent_titles: return False
    
    prompt = f"""
    لیست تیترهای اخیر: {recent_titles}
    تیتر جدید: '{new_title}'
    آیا این تیتر جدید دقیقاً همان خبری است که قبلاً در لیست بالا بوده؟ (حتی با کلمات متفاوت).
    فقط بنویس: YES یا NO
    """
    try:
        return "YES" in model.generate_content(prompt).text.strip().upper()
    except: return False

def send_to_telegram(message, image_url=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/" + ("sendPhoto" if image_url else "sendMessage")
        data = {"chat_id": CHANNEL_ID, "parse_mode": "Markdown"}
        if image_url:
            data["photo"] = image_url
            data["caption"] = message
        else:
            data["text"] = message
        requests.post(url, data=data)
    except Exception as e: print(f"Send Error: {e}")

def extract_image(entry):
    # استخراج عکس مخصوص زومیت
    try:
        if 'media_content' in entry: return entry.media_content[0]['url']
        if 'links' in entry:
            for l in entry.links:
                if l.type.startswith('image/'): return l.href
        if 'summary' in entry:
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img = soup.find('img')
            if img: return img['src']
    except: pass
    return None

def summarize_with_ai(title, content):
    prompt = f"""
    تو ادمین کانال تکنولوژی هستی.
    خبر: {title}
    متن: {content}

    وظایف:
    1. یک خلاصه جذاب و کوتاه (حدود 3 خط) به فارسی بنویس.
    2. لینک منبع نگذار.
    3. از ایموجی استفاده کن.
    4. در آخر بنویس: 🆔 @Teklp
    """
    try: return model.generate_content(prompt).text
    except: return None

def check_feeds():
    history_lines = load_history()
    history_links = [line.split("|")[0] for line in history_lines]
    
    # بررسی 40 دقیقه اخیر (امن برای اجرای 30 دقیقه‌ای)
    time_threshold = datetime.now() - timedelta(minutes=40)
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    if pub_date > time_threshold:
                        if entry.link in history_links: continue
                        if check_is_duplicate_topic(entry.title, history_lines):
                            save_to_history(entry.link, entry.title)
                            continue
                        
                        summary = summarize_with_ai(entry.title, entry.summary)
                        if summary:
                            final_text = f"🔥 **{entry.title}**\n\n{summary}"
                            send_to_telegram(final_text, extract_image(entry))
                            save_to_history(entry.link, entry.title)
                            time.sleep(5)
        except Exception as e: print(f"Feed Error: {e}")

if __name__ == "__main__":
    check_feeds()

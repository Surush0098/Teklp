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

# لیست سایت‌ها (می‌توانی سایت‌های دیگر را هم اضافه کنی)
RSS_URLS = [
    "https://www.zoomit.ir/feed/",
    # "https://digiato.com/feed",
]

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')

HISTORY_FILE = "history.txt"

def load_history():
    """لود کردن تاریخچه خبرهای ارسال شده"""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_to_history(link, title):
    """ذخیره لینک و تیتر در تاریخچه و کامیت کردن به گیت‌هاب"""
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{link}|{title}\n")
        
        # دستورات گیت برای ذخیره دائمی
        os.system(f'git config --global user.name "News Bot"')
        os.system(f'git config --global user.email "bot@noreply.github.com"')
        os.system(f'git add {HISTORY_FILE}')
        os.system('git commit -m "Update history log"')
        os.system('git push')
    except Exception as e:
        print(f"خطا در ذخیره تاریخچه: {e}")

def check_is_duplicate_topic(new_title, history_lines):
    """از هوش مصنوعی می‌پرسد آیا این موضوع قبلاً پوشش داده شده؟"""
    # استخراج تیترهای قبلی از فایل هیستوری (50 تای آخر) <--- تغییر اینجاست
    recent_titles = []
    
    # اینجا عدد را به 50 تغییر دادیم تا حافظه قوی‌تری داشته باشد
    for line in history_lines[-50:]: 
        parts = line.split("|")
        if len(parts) > 1:
            recent_titles.append(parts[1])
    
    if not recent_titles:
        return False 

    prompt = f"""
    من لیستی از ۵۰ تیتر خبری که اخیراً در کانال گذاشتم دارم:
    {recent_titles}

    یک خبر جدید آمده با این تیتر:
    "{new_title}"

    آیا این خبر جدید، دقیقاً همان موضوعی را می‌گوید که یکی از خبرهای لیست بالا گفته؟ 
    (حساسیت بالا داشته باش. اگر شک داشتی که تکراری است، بگو YES).
    فقط و فقط پاسخ بده: YES یا NO
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().upper()
        if "YES" in text:
            return True
        return False
    except:
        return False

def send_to_telegram(message, image_url=None):
    try:
        if image_url:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            data = {"chat_id": CHANNEL_ID, "photo": image_url, "caption": message, "parse_mode": "Markdown"}
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {"chat_id": CHANNEL_ID, "text": message, "parse_mode": "Markdown"} 
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error sending: {e}")

def extract_image(entry):
    if 'media_content' in entry:
        for media in entry.media_content:
            if 'url' in media: return media['url']
    if 'links' in entry:
        for link in entry.links:
            if link.type.startswith('image/'): return link.href
    if 'summary' in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and 'src' in img.attrs: return img['src']
    return None

def summarize_with_ai(title, content):
    prompt = f"""
    ادمین کانال تکنولوژی هستی.
    خبر: {title}
    متن: {content}
    وظایف:
    1. متن جذاب، کوتاه (3 خط).
    2. بدون لینک منبع.
    3. ایموجی دار.
    4. آخرش بنویس: 🆔 @Teklp
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return None

def check_feeds():
    print("Reading history...")
    history_lines = load_history()
    history_links = [line.split("|")[0] for line in history_lines]

    # بررسی اخبار 6 ساعت اخیر
    time_threshold = datetime.now() - timedelta(hours=6)
    
    for url in RSS_URLS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime.fromtimestamp(mktime(entry.published_parsed))
                    
                    if pub_date > time_threshold:
                        # فیلتر ۱: لینک تکراری
                        if entry.link in history_links:
                            print(f"تکراری (لینک): {entry.title}")
                            continue
                        
                        # فیلتر ۲: موضوع تکراری (چک کردن با ۵۰ خبر آخر)
                        if check_is_duplicate_topic(entry.title, history_lines):
                            print(f"تکراری (موضوع): {entry.title}")
                            save_to_history(entry.link, entry.title)
                            continue

                        print(f"خبر یونیک: {entry.title}")
                        image_url = extract_image(entry)
                        summary = summarize_with_ai(entry.title, entry.summary)
                        
                        if summary:
                            final_text = f"🔥 **{entry.title}**\n\n{summary}"
                            send_to_telegram(final_text, image_url)
                            save_to_history(entry.link, entry.title)
                            time.sleep(5)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_feeds()

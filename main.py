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

# منبع: زومیت
RSS_URLS = [
    "https://www.zoomit.ir/feed/",
]

# مدل قدرتمند با سهمیه 1000 تایی
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3.1-flash-lite')

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
    آیا این تیتر جدید دقیقاً همان خبری است که قبلاً فرستادیم؟ (حتی اگر کلماتش کمی فرق دارد).
    فقط بنویس: YES یا NO
    """
    try:
        res = model.generate_content(prompt).text.strip().upper()
        time.sleep(2)
        return "YES" in res
    except: 
        return False

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
    # دستور آپدیت شده با طول متن بیشتر (5 تا 11 خط)
    prompt = f"""
    تو سردبیر ارشد یک کانال تکنولوژی فارسی هستی.
    تیتر خبر: {title}
    متن خبر: {content}

    وظایف تو:
    1. **خلاصه سازی دقیق:** متن را تحلیل کن و نکات جذاب، اعداد و ارقام مهم و جزئیات فنی را بیرون بکش.
    2. **طول متن:** دستت باز است. متن باید "کامل و پرمحتوا" باشد (بین 5 تا 11 خط). اگر خبر مهمی است، تا 11 خط بنویس تا حق مطلب ادا شود. اگر خبر کوتاه است، همان 5 خط کافیست.
    3. **لحن:** حرفه‌ای، روان و ژورنالیستی (نه خشک، نه لودگی). از ایموجی‌های مرتبط استفاده کن.
    4. **پاورقی هوشمند (بسیار مهم):**
       - اگر در متن اسم شرکت، استارتاپ، تکنولوژی خاص یا فردی آمده که "گمنام" است (۹۰٪ مخاطبان عام نمی‌شناسند) و در متن توضیحی ندارد:
       - در انتهای پیام یک خط با علامت 💡 اضافه کن و خیلی کوتاه و مفید (نصف خط) آن را معرفی کن.
       - مثال: "💡 آنتروپیک: استارتاپ هوش مصنوعی رقیب OpenAI."
       - اگر همه چیز معروف بود (مثل اپل، سامسونگ، ایلان ماسک)، این بخش را کلاً ننویس.
    
    5. **قالب بندی:**
       - هیچ لینکی در متن نگذار.
       - در خط آخر فقط بنویس: 🆔 @Teklp
    """
    try: 
        response = model.generate_content(prompt).text
        time.sleep(4) 
        return response
    except: return None

def check_feeds():
    history_lines = load_history()
    history_links = [line.split("|")[0] for line in history_lines]
    
    # تایم 150 دقیقه برای اطمینان کامل
    time_threshold = datetime.now() - timedelta(minutes=150)
    
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

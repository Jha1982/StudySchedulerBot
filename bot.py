import requests
import pytz
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
import os
from dotenv import load_dotenv


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
URL = "https://nmc.udu.edu.ua/cgi-bin/timetable.cgi"

UA_TZ = pytz.timezone("Europe/Kiev")
TH_TZ = pytz.timezone("Asia/Bangkok")


def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def convert_time(time_str, date_str, target_tz):
    try:
        start, end = time_str.strip().split("–")
        dt_start = UA_TZ.localize(datetime.strptime(f"{date_str} {start.strip()}", "%d.%m.%Y %H:%M"))
        dt_end = UA_TZ.localize(datetime.strptime(f"{date_str} {end.strip()}", "%d.%m.%Y %H:%M"))
        da_start = dt_start.astimezone(target_tz).strftime("%H:%M")
        da_end = dt_end.astimezone(target_tz).strftime("%H:%M")
        return f"{da_start}–{da_end}"
    except:
        return time_str
    

def get_schedule():
    url = "https://nmc.udu.edu.ua/cgi-bin/timetable.cgi"
    headers = {"User-Agent": "Mozilla/5.0"}
    data = {
        "faculty": "0",
        "teacher": "0",
        "course": "0",
        "group": "2-033",
        "sdate": "",
        "edate": "",
        "n": "700"
    }

    response = requests.post(url, data=data, headers=headers, verify=False, timeout=30)
    response.encoding = "cp1251"
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ")

    today = datetime.now(UA_TZ).replace(tzinfo=None)
    today_ua = datetime.now(UA_TZ).replace(tzinfo=None)

    #print(f"today (Danang): {today}")
    #print(f"today_ua (Ukraine): {today_ua}")
    
    today_str = today.strftime("%d.%m.%Y")
    start_week = today
    end_week = today + timedelta(days=7)
    week_str = f"{start_week.strftime('%d.%m.%Y')} — {end_week.strftime('%d.%m.%Y')}"

    months = {
        "01": "СІЧЕНЬ", "02": "ЛЮТИЙ", "03": "БЕРЕЗЕНЬ",
        "04": "КВІТЕНЬ", "05": "ТРАВЕНЬ", "06": "ЧЕРВЕНЬ",
        "07": "ЛИПЕНЬ", "08": "СЕРПЕНЬ", "09": "ВЕРЕСЕНЬ",
        "10": "ЖОВТЕНЬ", "11": "ЛИСТОПАД", "12": "ГРУДЕНЬ"
    }
    month_name = months[today.strftime("%m")]

    weekdays = {
        0: "ПОНЕДІЛОК", 1: "ВІВТОРОК", 2: "СЕРЕДА",
        3: "ЧЕТВЕР", 4: "ПʼЯТНИЦЯ", 5: "СУБОТА", 6: "НЕДІЛЯ"
    }
    weekdaysShort = {
        0: "Пн", 1: "Вт", 2: "Ср",
        3: "Чт", 4: "Пт", 5: "Сб", 6: "Нд"
    }

    today_name = weekdaysShort[today.weekday()]
    days = re.split(r'(\d{2}\.\d{2}\.\d{4})', text)

    result = f"📅 {month_name}  |  {week_str}\n"
    result += f"🎯 Сьогодні: {today_name}, {today_str}\n\n\n"
    #result += f"{'─' * 20}\n\n"
    result += f"РОЗКЛАД\n\n"

    start_range = today_ua.date()
    end_range = today_ua.date() + timedelta(days=5)
    shown_dates = set()

    for i in range(1, len(days), 2):
        date = days[i]
        content = days[i + 1]

        # пропускаем если уже показали этот день
        if date in shown_dates:
            continue

        day_obj = datetime.strptime(date, "%d.%m.%Y")
        #print(f"date: {date}, in range: {start_range <= day_obj.date() <= end_range}")
       # start_range = today_ua.date()
       # end_range = today_ua.date() + timedelta(days=7)
        if not (start_range <= day_obj.date() <= end_range):
            continue

        weekday = weekdays[day_obj.weekday()]
        is_today = date == today_ua.strftime("%d.%m.%Y")
        day_block = ""

        pairs = re.split(r'(\d{2}:\d{2}\s*\d{2}:\d{2})', content)
        #print("ALL dates found:", days[1::2][:20])

        #print(f"date: {date}, pairs count: {len(pairs)}, content preview: {content[:100]}")


        for j in range(1, len(pairs), 2):
            time_raw = pairs[j]
            info = pairs[j + 1].strip()

            info = re.sub(r'зб\.гр\..*?(?=зав\.|$)', '', info)
            info = re.sub(r'\s+\d+$', '', info)
            info = re.sub(r'©.*', '', info).strip()

            if not info or re.fullmatch(r'\d+', info):
                continue

            link_match = re.search(r'https?://\S+', info)
            link = link_match.group(0) if link_match else ""
            if link:
                info = info.replace(link, '').strip()

            teacher_match = re.search(r'зав\.\s*кафедри\s+([А-ЯІЇЄҐA-Z][^\d]+)', info)
            teacher = teacher_match.group(1).strip() if teacher_match else ""
            if teacher:
                info = info.replace(teacher, '').strip()
                info = re.sub(r'зав\.\s*кафедри', '', info).strip()

            type_match = re.search(r'\((Л|Пр|Лб|С)\)', info)
            if type_match:
                type_map = {"Л": "Лекція", "Пр": "Практика", "Лб": "Лабораторна", "С": "Семінар"}
                lesson_type = type_map.get(type_match.group(1), type_match.group(1))
                info = info.replace(type_match.group(0), '').strip()
            else:
                lesson_type = ""

            subject = escape_html(info.strip())
            teacher = escape_html(teacher)
            time = convert_time(time_raw.replace(" ", "–"), date, TH_TZ)


            block = f"⏰ {time}"
            if lesson_type:
                block += f"  |  {lesson_type}"
            block += "\n"
            block += f"{subject}\n"

            line = []
            if teacher:
                line.append(f"👤 {teacher}")
            if link:
                line.append(f"<a href='{link}'>🔗 Посилання</a>")
            if line:
                block += "  |  ".join(line) + "\n"
            block += "· · · · · · · · · · · · · · · · · · · · ·\n\n"

            day_block += block

        if day_block.strip():
            shown_dates.add(date)  # добавь эту строку
            if is_today:
                header = f"⭐️ СЬОГОДНІ — {weekday}, {date}\n"
            else:
                header = f"📆 {weekday}, {date}\n"
            result += header
            result += f"{'─' * 12}\n"
            result += day_block
            result += "\n"
        
    return result[:4096]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 Бот розкладу\n\n"
        "Команди:\n"
        "/schedule — показати розклад\n"
    )


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Завантажую розклад...")
    try:
        text = get_schedule()
        await update.message.reply_text(text[:4096], parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schedule", schedule))
    app.run_polling()


if __name__ == "__main__":
    main()
import requests
import pandas as pd
import pytz
from bs4 import BeautifulSoup
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

BOT_TOKEN = "PASTE_YOUR_TOKEN_HERE"
URL = "https://nmc.udu.edu.ua/cgi-bin/timetable.cgi?n=700"

UA_TZ = pytz.timezone("Europe/Kiev")
TH_TZ = pytz.timezone("Asia/Bangkok")

def get_schedule():
    response = requests.get(URL)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")

    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    df = pd.DataFrame(rows, columns=headers)

    def to_th_time(t):
        try:
            base = datetime.strptime(t, "%H:%M")
            now = datetime.now()
            ua = UA_TZ.localize(
                datetime(now.year, now.month, now.day,
                         base.hour, base.minute)
            )
            return ua.astimezone(TH_TZ).strftime("%H:%M")
        except:
            return t

    df.iloc[:, 0] = df.iloc[:, 0].apply(to_th_time)
    return df

def df_to_text(df):
    text = ""
    for _, row in df.iterrows():
        text += f"🕒 {row[0]}\n"
        for col in df.columns[1:]:
            if row[col]:
                text += f"   • {col}: {row[col]}\n"
        text += "\n"
    return text[:4000]  # лимит Telegram

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 Бот расписания\n\n"
        "Команды:\n"
        "/schedule — показать расписание\n"
    )

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Загружаю расписание...")
    try:
        df = get_schedule()
        text = df_to_text(df)
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schedule", schedule))
    app.run_polling()

if __name__ == "__main__":
    main()

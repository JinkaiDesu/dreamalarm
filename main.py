# === IMPORTS ===
import os
import asyncio
import logging
import schedule
import threading
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from datetime import datetime, time
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === Ld Vars ===
load_dotenv()

# === Sheets Setup ===
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive'] # Define the scopes for Google Sheets and Google Drive
SHEET_NAME = os.getenv("SHEET_NAME") # Google Sheets Name


# === Login Credentials ===
creds = Credentials.from_service_account_file(
    "creds.json", scopes = SCOPES) # Load the credentials from the JSON file
client = gspread.authorize(creds) # Authorize the client with the credentials
sheet = client.open(SHEET_NAME).sheet1 # Open the Google Sheet and select the first sheet
#for sheet in client.openall():    # See all Sheets the client has access to
#   print(sheet.title)             # DEBUG: print Sheets client sees

# === CONFIG ===
BOT_TOKEN = os.getenv('BOT_TOKEN') # Telegram Bot Token (DreamBOT)
YOUR_CHAT_ID = os.getenv('CHAT_ID') # TODO: Add support for multiple user's and chat ID's
ping_interval_minutes = 5 # Notification every 'x' min

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("DreamBot activated. Logging begins."
                                        )  # Send a message to the user

message_log = [] # List to store message log

# === LOGGING ===
async def log_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_text = update.message.text  # Get the text from the user
        timestamp = update.message.date.isoformat(
        )  # Get the timestamp from the message
        username = update.message.from_user.username or update.message.from_user.first_name  # Get the username or first name from the user
        log_entry = f"{timestamp} - {user_text}"  # Create a log entry
        message_log.append(
            log_entry)  # Append the log entry to the message log
        logging.info(log_entry)  # Log the entry to the console

        try:
            sheet.append_row([timestamp, username,
                              user_text])  # Append to Google Sheets
        except Exception as e:
            logging.error(f"Google Sheets logging failed: {e}")


# === PING ===
async def ping():
    try:
        bot = Bot(token=BOT_TOKEN) # Create a bot instance
        await bot.send_message(chat_id=YOUR_CHAT_ID, text="⏰ Log check-in: What are you doing right now?") # Send ping message
    except Exception as e:
        logging.error(f"Ping error: {e}")


# === SCHEDULER ===
def run_schedule_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Schedule the ping function to run every 5 minutes
    async def schedule_runner():
        while True:
            schedule.run_pending()  # Run all pending jobs
            await asyncio.sleep(1)

    loop.run_until_complete(
        schedule_runner())  # Run the schedule runner until complete


# === HRS OF OPS ===
def is_within_hours():
    now = datetime.now().time()  # Get current time
    return time(4, 30) <= now <= time(22, 0)  #Working Hours


# === MAIN ===
def main():
    # Create the Application and pass it your bot's token.
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # on different commands - answer in Telegram
    app.add_handler(CommandHandler("start", start))  # Start command
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND,
                       log_response))  # Log all text messages

    # Schedule ping
    def is_precise_ping_time():
        now = datetime.now()  # Get current time
        return now.minute % ping_interval_minutes == 0 and now.second == 0  # Check if current minute is a multiple of ping interval and second is 0

    # Precise ping loop
    async def precise_ping_loop():
        while True:
            if is_within_hours and is_precise_ping_time(
            ):  # Check if within hours of operation and precise ping time
                await ping()  # Send ping
                await asyncio.sleep(1.2)  # prevent double-send in same second
            await asyncio.sleep(0.5)  # check every 0.5 seconds

    # Run precise ping loop in a separate thread
    def run_schedule_loop():
        loop = asyncio.new_event_loop()  # Create a new event loop
        asyncio.set_event_loop(
            loop)  # Set the new event loop as the current event loop
        loop.run_until_complete(
            precise_ping_loop())  # Run the precise ping loop until complete

    # Run scheduler in a separate thread
    threading.Thread(target=run_schedule_loop, daemon=True).start()

    # Start the bot (blocking)
    app.run_polling()


# === ENTRY POINT ===
if __name__ == "__main__":
    # Run the main function
    main()

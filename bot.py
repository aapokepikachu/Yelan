import logging
import os
import asyncio
import pymongo
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import FastAPI
import uvicorn

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
CHANNEL_IDS = list(map(int, os.getenv("CHANNEL_IDS").split(',')))

# Initialize bot and dispatcher
session = AiohttpSession()
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML, session=session)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# MongoDB connection
client = pymongo.MongoClient(MONGO_URI)
db = client["yelan_bot"]
requests_collection = db["rom_requests"]
search_collection = db["search_logs"]

# Logging setup
logging.basicConfig(level=logging.INFO)

# Cooldown storage
user_cooldowns = {}

# FastAPI for Render Web Service
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Yelan Bot is Running!"}

# Start message
async def start_message():
    return (
        "👋 Hello! I'm Yelan, your Pokémon ROM Finder! 🎮\n\n"
        "Use /find <ROM Name> to search for a ROM.\n"
        "Press 'Help ℹ️' to see my commands."
    )

# Inline buttons
def main_menu():
    buttons = [
        [InlineKeyboardButton(text="Help ℹ️", callback_data="help"),
         InlineKeyboardButton(text="About Me 🤗", callback_data="about")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("Back 🔙", callback_data="back")]])

# /start command
@dp.message(F.text.startswith("/start"))
async def start_command(message: types.Message):
    await message.answer(await start_message(), reply_markup=main_menu())

# Inline button handlers
@dp.callback_query(F.data == "help")
async def help_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📌 Commands List:\n"
        "/find <ROM Name> - Search for a ROM\n"
        "/request - Request a ROM (24h cooldown) ⏳\n"
        "/latest - View latest uploads 📥\n"
        "/featured - Check featured ROMs ⭐\n"
        "/trending - View trending ROMs 🔥\n"
        "/cancel - Cancel an ongoing process ❌\n"
        "/ping - Check bot response time 📡\n"
        "/mystery - Get a Pokémon fact/joke 🎭\n"
        "/shinyhunt - See a random Shiny Pokémon ✨\n"
        "/help_link - Get command links 🔗",
        reply_markup=back_button()
    )

@dp.callback_query(F.data == "about")
async def about_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👤 Owner: @AAPoke\n"
        "🛠 Creator: @PokemonBots\n"
        "💰 Monetization: @PokemonNdsGba",
        reply_markup=back_button()
    )

@dp.callback_query(F.data == "back")
async def back_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(await start_message(), reply_markup=main_menu())

# /find command (optimized)
@dp.message(F.text.startswith("/find"))
async def find_rom(message: types.Message):
    query = message.text.replace("/find", "").strip().lower()
    if not query:
        await message.reply("⚠️ Please provide a ROM name. Example: /find Pokémon Emerald")
        return

    found_results = []
    for channel_id in CHANNEL_IDS:
        async for msg in bot.get_chat_history(channel_id, limit=200):
            if msg.caption and query in msg.caption.lower():
                link = f"https://t.me/c/{str(channel_id)[4:]}/{msg.message_id}"
                found_results.append(f"📂 {msg.caption}\n🔗 [Download Here]({link})")

    if found_results:
        await message.reply("\n\n".join(found_results[:5]), disable_web_page_preview=True)
        search_collection.insert_one({"query": query, "timestamp": datetime.utcnow()})
    else:
        await message.reply(f"❌ No results found for '{query}'. Try /request to ask admins.")

# /request command (24h cooldown)
@dp.message(F.text.startswith("/request"))
async def request_rom(message: types.Message):
    user_id = message.from_user.id
    last_request = user_cooldowns.get(user_id)

    if last_request and datetime.now() - last_request < timedelta(hours=24):
        await message.reply("⏳ You've already requested a ROM in the last 24 hours.")
        return

    user_cooldowns[user_id] = datetime.now()
    requests_collection.insert_one({"user_id": user_id, "username": message.from_user.username, "date": datetime.now()})
    await bot.send_message(ADMIN_GROUP_ID, f"📩 New ROM Request!\n👤 User: @{message.from_user.username}")
    await message.reply("📨 ROM request sent to admins!")

# /latest command
@dp.message(F.text.startswith("/latest"))
async def latest_uploads(message: types.Message):
    uploads = []
    for channel_id in CHANNEL_IDS:
        async for msg in bot.get_chat_history(channel_id, limit=5):
            link = f"https://t.me/c/{str(channel_id)[4:]}/{msg.message_id}"
            uploads.append(f"📂 {msg.caption}\n🔗 [Download]({link})")

    await message.reply("\n\n".join(uploads) if uploads else "🚨 No latest uploads found.")

# /trending command
@dp.message(F.text.startswith("/trending"))
async def trending_roms(message: types.Message):
    trends = search_collection.aggregate([
        {"$group": {"_id": "$query", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ])
    result = "\n".join([f"🔥 {t['_id']} - {t['count']} searches" for t in trends])
    await message.reply(f"📊 Trending ROMs:\n\n{result if result else 'No trends yet!'}")

# /featured command
@dp.message(F.text.startswith("/featured"))
async def featured_roms(message: types.Message):
    featured_list = [
        "⭐ Pokémon FireRed Enhanced 🔗 [Download Link](https://example.com)",
        "⭐ Pokémon Emerald Kaizo 🔗 [Download Link](https://example.com)",
        "⭐ Pokémon Gaia 🔗 [Download Link](https://example.com)"
    ]
    await message.reply("\n".join(featured_list), disable_web_page_preview=True)

# /help command
@dp.message(F.text.startswith("/help"))
async def help_command(message: types.Message):
    await message.reply("🔗 Command Links:\n"
                        "/find - Search ROMs\n"
                        "/request - Request ROMs\n"
                        "/latest - Latest uploads\n"
                        "/featured - Featured ROMs\n"
                        "/trending - Trending ROMs\n"
                        "/ping - Bot Status\n"
                        "/mystery - Fun Facts\n"
                        "/shinyhunt - Shiny Hunt")

# Start the bot
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

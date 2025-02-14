import logging
import os
import asyncio
import pymongo
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from fastapi import FastAPI
import uvicorn
from datetime import datetime, timedelta

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
CHANNEL_IDS = os.getenv("CHANNEL_IDS").split(',')

# Initialize bot, dispatcher & storage
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Connect to MongoDB
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

# 🏁 START COMMAND
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    buttons = InlineKeyboardMarkup(row_width=2)
    buttons.add(
        InlineKeyboardButton("Help ℹ️", callback_data="help"),
        InlineKeyboardButton("About Me 🤗", callback_data="about")
    )
    await message.answer(
        f"👋 Hello {message.from_user.first_name}! I'm Yelan, your Pokémon ROM Finder! 🎮\n\n"
        "Use /find <ROM Name> to search for a ROM or press 'Help ℹ️' to see my commands.",
        reply_markup=buttons
    )

# ℹ️ HELP BUTTON HANDLER
@dp.callback_query_handler(lambda c: c.data == "help")
async def help_callback(callback_query: types.CallbackQuery):
    await callback_query.message.answer(
        "📌 Commands List:\n"
        "/find <ROM Name> - Search for a ROM\n"
        "/request - Request a ROM (24h cooldown) ⏳\n"
        "/latest - View latest uploads 📥\n"
        "/featured - Check featured ROMs ⭐\n"
        "/trending - View trending ROMs 🔥\n"
        "/cancel - Cancel an ongoing process ❌\n"
        "/ping - Check bot response time 📡\n"
        "/mystery - Get a Pokémon fact/joke 🎭\n"
        "/shinyhunt - See a random Shiny Pokémon ✨"
    )

# 🤗 ABOUT ME BUTTON HANDLER
@dp.callback_query_handler(lambda c: c.data == "about")
async def about_callback(callback_query: types.CallbackQuery):
    await callback_query.message.answer(
        "👤 Owner: @AAPoke\n"
        "🛠 Creator: @PokemonBots\n"
        "💰 Monetization: @PokemonNdsGba"
    )

# 🔍 FIND COMMAND
@dp.message_handler(commands=["find"])
async def find_rom(message: types.Message):
    query = message.text.replace("/find", "").strip()
    if not query:
        await message.reply("⚠️ Please provide a ROM name. Example: /find Pokémon Emerald")
        return

    found = False
    for channel_id in CHANNEL_IDS:
        async for msg in bot.iter_history(int(channel_id), limit=50):
            if query.lower() in msg.text.lower():
                await message.reply(f"✅ ROM Found!\n\n📂 {msg.text}\n🔗 Download Link")
                found = True
                break

    if not found:
        await message.reply(f"❌ No results found for '{query}'. Try /request to ask admins.")

# 📩 REQUEST COMMAND (WITH 24H COOLDOWN)
@dp.message_handler(commands=["request"])
async def request_rom(message: types.Message):
    user_id = message.from_user.id
    last_request = user_cooldowns.get(user_id)

    if last_request and datetime.now() - last_request < timedelta(hours=24):
        await message.reply("⏳ You've already requested a ROM in the last 24 hours. Please wait.")
        return

    user_cooldowns[user_id] = datetime.now()
    requests_collection.insert_one({"user_id": user_id, "username": message.from_user.username, "date": datetime.now()})
    await bot.send_message(ADMIN_GROUP_ID, f"📩 New ROM Request!\n👤 User: @{message.from_user.username}")
    await message.reply("📨 ROM request sent to admins! Please wait for approval.")

# 📥 LATEST UPLOADS
@dp.message_handler(commands=["latest"])
async def latest_uploads(message: types.Message):
    uploads = []
    for channel_id in CHANNEL_IDS:
        async for msg in bot.iter_history(int(channel_id), limit=5):
            uploads.append(f"📂 {msg.text}\n🔗 Download")
        if uploads:
            break

    if uploads:
        await message.reply("\n\n".join(uploads))
    else:
        await message.reply("🚨 No latest uploads found.")

# 🚀 TRENDING ROMS
@dp.message_handler(commands=["trending"])
async def trending_roms(message: types.Message):
    trends = search_collection.aggregate([
        {"$group": {"_id": "$query", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ])
    result = "\n".join([f"🔥 {t['_id']} - {t['count']} searches" for t in trends])
    await message.reply(f"📊 Trending ROMs:\n\n{result if result else 'No trends yet!'}")

# 🛠 PING COMMAND
@dp.message_handler(commands=["ping"])
async def ping_command(message: types.Message):
    await message.reply("🏓 Pong! The bot is active and running.")

# 🎭 MYSTERY COMMAND
@dp.message_handler(commands=["mystery"])
async def mystery_command(message: types.Message):
    facts = [
        "🎭 Did you know? Pikachu’s name comes from the Japanese words ‘pika’ (sparkle) and ‘chu’ (squeak)!",
        "🎭 Charizard was originally called ‘Lizardon’ in Japan!",
        "🎭 Wobbuffet’s real body is hidden behind its blue ‘punching bag’ form!"
    ]
    await message.reply(facts[datetime.now().second % len(facts)])

# ✨ SHINY HUNT COMMAND
@dp.message_handler(commands=["shinyhunt"])
async def shinyhunt_command(message: types.Message):
    await message.reply("✨ You found a Shiny Pokémon! 🔗 View Here")

# 🚀 ASYNC FUNCTION TO START TELEGRAM BOT
async def start_bot():
    logging.info("Starting Telegram bot...")
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()  # ✅ Fix for unclosed client session

# 🚀 MAIN FUNCTION TO RUN BOT & FASTAPI TOGETHER
async def main():
    bot_task = asyncio.create_task(start_bot())  

    # ✅ Correct way to run FastAPI inside an async event loop
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  
    server = uvicorn.Server(config)  
    server_task = asyncio.create_task(server.serve())  

    await asyncio.gather(bot_task, server_task)  

if __name__ == "__main__":
    asyncio.run(main())  # ✅ Runs everything properly

import logging
import os
import asyncio
import pymongo
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.session.middlewares.request_logging import RequestLogging
from fastapi import FastAPI
import uvicorn
from datetime import datetime, timedelta

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID"))
CHANNEL_IDS = [int(ch) for ch in os.getenv("CHANNEL_IDS").split(',')]

# Initialize bot & dispatcher
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["yelan_bot"]
requests_collection = db["rom_requests"]
search_collection = db["search_logs"]

# Logging setup
logging.basicConfig(level=logging.INFO)
bot.session.middleware(RequestLogging())

# Cooldown storage
user_cooldowns = {}

# FastAPI for Render Web Service
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Yelan Bot is Running!"}

# 🏁 START COMMAND
@dp.message(Command("start"))
async def start_command(message: types.Message):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Help ℹ️", callback_data="help"),
         InlineKeyboardButton(text="About Me 🤗", callback_data="about")]
    ])
    
    text = (f"👋 Hello {message.from_user.first_name}! I'm Yelan, your Pokémon ROM Finder! 🎮\n\n"
            "Use <code>/find &lt;ROM Name&gt;</code> to search for a ROM.\n\n"
            "🔎 <b>Commands:</b>\n"
            "• /find <ROM Name> - Search for a ROM\n"
            "• /request - Request a ROM (24h cooldown)\n"
            "• /latest - View latest uploads\n"
            "• /featured - Check featured ROMs\n"
            "• /trending - View trending ROMs\n"
            "• /ping - Check bot response time\n"
            "• /mystery - Get a Pokémon fact/joke\n"
            "• /shinyhunt - See a random Shiny Pokémon")
    
    await message.answer(text, reply_markup=buttons)

# ℹ️ HELP & ABOUT ME BUTTON HANDLER (Updates Message)
@dp.callback_query(F.data.in_(["help", "about", "back"]))
async def callback_handler(callback: types.CallbackQuery):
    text, buttons = None, None
    
    if callback.data == "help":
        text = ("📌 <b>Commands List:</b>\n"
                "• /find <ROM Name> - Search for a ROM\n"
                "• /request - Request a ROM (24h cooldown)\n"
                "• /latest - View latest uploads\n"
                "• /featured - Check featured ROMs\n"
                "• /trending - View trending ROMs\n"
                "• /ping - Check bot response time\n"
                "• /mystery - Get a Pokémon fact/joke\n"
                "• /shinyhunt - See a random Shiny Pokémon")
    elif callback.data == "about":
        text = ("👤 <b>Owner:</b> @AAPoke\n"
                "🛠 <b>Creator:</b> @PokemonBots\n"
                "💰 <b>Monetization:</b> @PokemonNdsGba")
    else:
        await start_command(callback.message)
        return
    
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back 🔙", callback_data="back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=buttons)

# 🔍 FIND COMMAND (Now Searches File Captions)
@dp.message(Command("find"))
async def find_rom(message: types.Message):
    query = message.text.replace("/find", "").strip()
    if not query:
        await message.reply("⚠️ Please provide a ROM name. Example: <code>/find Pokémon Emerald</code>")
        return

    found = False
    results = []

    for channel_id in CHANNEL_IDS:
        async for msg in bot.get_chat_history(channel_id, limit=50):
            if msg.caption and query.lower() in msg.caption.lower():
                results.append(f"📂 <b>{msg.caption}</b>\n🔗 <a href='{msg.link}'>Download Here</a>")
                found = True
            if len(results) >= 5:
                break

    if results:
        await message.reply("\n\n".join(results), disable_web_page_preview=True)
    else:
        await message.reply(f"❌ No results found for '{query}'. Try <code>/request</code> to ask admins.")

# 📩 REQUEST COMMAND (WITH 24H COOLDOWN)
@dp.message(Command("request"))
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

# 🛠 PING COMMAND
@dp.message(Command("ping"))
async def ping_command(message: types.Message):
    await message.reply("🏓 Pong! The bot is active and running.")

# 🎭 MYSTERY COMMAND
@dp.message(Command("mystery"))
async def mystery_command(message: types.Message):
    facts = [
        "🎭 Did you know? Pikachu’s name comes from the Japanese words ‘pika’ (sparkle) and ‘chu’ (squeak)!",
        "🎭 Charizard was originally called ‘Lizardon’ in Japan!",
        "🎭 Wobbuffet’s real body is hidden behind its blue ‘punching bag’ form!"
    ]
    await message.reply(facts[datetime.now().second % len(facts)])

# ✨ SHINY HUNT COMMAND
@dp.message(Command("shinyhunt"))
async def shinyhunt_command(message: types.Message):
    await message.reply("✨ You found a Shiny Pokémon! 🔗 View Here")

# 🚀 ASYNC FUNCTION TO START TELEGRAM BOT
async def main():
    bot_task = asyncio.create_task(dp.start_polling(bot))

    # ✅ Correct way to run FastAPI inside an async event loop
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  
    server = uvicorn.Server(config)  
    server_task = asyncio.create_task(server.serve())  

    await asyncio.gather(bot_task, server_task)  

if __name__ == "__main__":
    asyncio.run(main())  # ✅ Runs everything properly

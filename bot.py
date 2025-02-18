import os
import asyncio
import threading
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
import web

# Load environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

# Initialize bot and MongoDB
bot = Client("yelan", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client["yelan_db"]

START_TEXT = "Hi {name}, I am Yelan. You can send your ROM request by /request command."
START_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("Help ℹ️", callback_data="help"),
     InlineKeyboardButton("About me 🤗", callback_data="about")]
])

HELP_TEXT = """**Commands:**
/start - Start message  
/help - Show this help  
/about - About the bot  
/request - Request a ROM  
/track - Track request  
/ping - Show latency  

**Admin Commands:**
/done <request_number> - Mark request complete  
/send <telegram_id> - Send user a message  
/broadcast - Broadcast message  
/db - Show database details"""

ABOUT_TEXT = """**About Me:**  
Owner: [AAPoke](https://telegram.dog/AAPoke)  
Creator: @PokemonBots  
Monetization: @PokemonNdsGba"""

BACK_BUTTON = InlineKeyboardMarkup([[InlineKeyboardButton("Back 🔙", callback_data="start")]])

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(START_TEXT.format(name=message.from_user.first_name), reply_markup=START_BUTTONS)

@bot.on_callback_query()
async def callback_handler(client, query):
    if query.data == "help":
        await query.message.edit_text(HELP_TEXT, reply_markup=BACK_BUTTON)
    elif query.data == "about":
        await query.message.edit_text(ABOUT_TEXT, reply_markup=BACK_BUTTON)
    elif query.data == "start":
        await query.message.edit_text(START_TEXT.format(name=query.from_user.first_name), reply_markup=START_BUTTONS)

@bot.on_message(filters.command("help"))
async def help_command(client, message):
    await message.reply_text(HELP_TEXT, reply_markup=BACK_BUTTON)

@bot.on_message(filters.command("about"))
async def about_command(client, message):
    await message.reply_text(ABOUT_TEXT, reply_markup=BACK_BUTTON)

@bot.on_message(filters.command("request"))
async def request_command(client, message):
    user_id = message.from_user.id
    last_request = await db.requests.find_one({"user_id": user_id})

    if last_request and datetime.utcnow() - last_request["timestamp"] < timedelta(hours=24):
        return await message.reply_text("You can only send one request every 24 hours.")

    # Prompt user to send ROM request
    await message.reply_text("Which ROM are you requesting? Send your request or use /cancel.")
    await db.requests.update_one({"user_id": user_id}, {"$set": {"status": "waiting"}}, upsert=True)

@bot.on_message(filters.text & ~filters.command(["cancel", "request"]))
async def receive_request(client, message):
    user_id = message.from_user.id
    request_entry = await db.requests.find_one({"user_id": user_id, "status": "waiting"})

    if request_entry:
        # Check if request_id is set; if not, generate one
        request_id = request_entry.get("request_id")
        if not request_id:
            request_id = await db.requests.count_documents({}) + 1  # Generate request_id if not present

        # Update the request details in the database
        await db.requests.update_one({"user_id": user_id}, {"$set": {
            "request_id": request_id,
            "request": message.text,
            "timestamp": datetime.utcnow(),
            "status": "pending"
        }})

        # Send request to admin group
        request_details = f"**New ROM Request:**\nRequest ID: {request_id}\nUser: {message.from_user.username or 'No Username'}\nUser ID: {user_id}\nRequest: {message.text}"
        await client.send_message(GROUP_ID, request_details)

        await message.reply_text(f"Your request has been sent to the Admins. Request ID: {request_id}")

@bot.on_message(filters.command("cancel"))
async def cancel_request(client, message):
    user_id = message.from_user.id
    await db.requests.delete_one({"user_id": user_id, "status": "waiting"})
    await message.reply_text("Your request process has been cancelled.")

@bot.on_message(filters.command("track"))
async def track_request(client, message):
    user_id = message.from_user.id
    request = await db.requests.find_one({"user_id": user_id})

    if not request:
        await message.reply_text("No request sent.")
    else:
        status = request.get("status", "Unknown")
        await message.reply_text(f"Request ID: {request['request_id']}\nStatus: {status}")

@bot.on_message(filters.command("ping"))
async def ping_command(client, message):
    start_time = datetime.utcnow()
    reply = await message.reply_text("Pong!")
    latency = (datetime.utcnow() - start_time).microseconds / 1000
    await reply.edit_text(f"Pong! `{latency}ms`")

@bot.on_message(filters.command("done"))
async def mark_done(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("You are not authorized to use this command.")

    if len(message.command) < 2:
        return await message.reply_text("Please provide a request ID.")

    try:
        request_id = int(message.command[1])
        request = await db.requests.find_one({"request_id": request_id})

        if request:
            await db.requests.update_one({"request_id": request_id}, {"$set": {"status": "Completed ✅"}})
            await client.send_message(request["user_id"], "Your request has been completed ✅")
            await message.reply_text("Marked as completed.")
        else:
            await message.reply_text("Request ID not found.")
    except ValueError:
        await message.reply_text("Invalid request ID. It must be an integer.")

@bot.on_message(filters.command("send"))
async def send_message(client, message):
    if not is_admin(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("Reply to a message and use /send <telegram_id>")

    try:
        user_id = int(message.command[1])
        await client.send_message(user_id, message.reply_to_message.text)
        await message.reply_text("Message sent.")
    except IndexError:
        await message.reply_text("Please provide a valid user ID.")
    except ValueError:
        await message.reply_text("Invalid user ID.")

@bot.on_message(filters.command("broadcast"))
async def broadcast(client, message):
    if not is_admin(message.from_user.id) or not message.reply_to_message:
        return await message.reply_text("Reply to a message to broadcast.")

    users = await db.requests.distinct("user_id")
    for user in users:
        try:
            await client.send_message(user, message.reply_to_message.text)
        except Exception as e:
            print(f"Failed to send message to {user}: {e}")
            pass
    await message.reply_text(f"Broadcast sent to {len(users)} users.")

@bot.on_message(filters.command("db"))
async def db_stats(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("You are not authorized.")

    count = await db.requests.count_documents({})
    await message.reply_text(f"Total requests: {count}")

def run_flask():
    web.app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run()
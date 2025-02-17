import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import pymongo
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from aiohttp import web

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS").split(",")  # Admin user IDs separated by commas
GROUP_A_CHAT_ID = os.getenv("GROUP_A_CHAT_ID")
MONGO_URI = os.getenv("MONGO_URI")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Connect to MongoDB using the connection string (if you're using MongoDB Atlas, this will include 'mongodb+srv' in the URI)
client = pymongo.MongoClient(MONGO_URI)
db = client['yelan_bot']
requests_collection = db['requests']

# Enable logging
logging.basicConfig(level=logging.INFO)

# User requests cooldown dictionary (to implement 24-hour cooldown)
user_cooldowns = {}

# Start command
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Help ℹ️", callback_data="help"),
        InlineKeyboardButton("About me 🤗", callback_data="about")
    )
    await message.answer(f"Hi {user_name}, I am Yelan. You can send your ROM request by /request command.", reply_markup=keyboard)

# Help command (Inline Button)
@dp.callback_query_handler(lambda c: c.data == 'help')
async def process_help(callback_query: types.CallbackQuery):
    help_text = """
    1) /start - Start the bot and greet the user.
    2) /help - Get help with available commands.
    3) /about - Get bot information.

    4) /request - Submit a ROM request. The bot will forward your request to admins.
    5) /track - Track your request status.
    6) /ping - Check the bot's latency.

    (Admins only):
    7) /done <request_number> - Mark a request as completed and notify the user.
    8) /send <telegram_id> - Send a message to a specific user.
    9) /broadcast - Send a message to all users and track delivery status.
    10) /db - View database details and storage usage.
    """
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Back 🔙", callback_data="back"))
    await callback_query.message.answer(help_text, reply_markup=keyboard)

# About me command (Inline Button)
@dp.callback_query_handler(lambda c: c.data == 'about')
async def process_about(callback_query: types.CallbackQuery):
    about_text = """
    About me:
    Owner: (AAPoke)[https://telegram.dog/AAPoke]
    Creator: @PokemonBots
    Monetization: @PokemonNdsGba
    """
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Back 🔙", callback_data="back"))
    await callback_query.message.answer(about_text, reply_markup=keyboard)

# Back button handler
@dp.callback_query_handler(lambda c: c.data == 'back')
async def process_back(callback_query: types.CallbackQuery):
    user_name = callback_query.from_user.first_name
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Help ℹ️", callback_data="help"),
        InlineKeyboardButton("About me 🤗", callback_data="about")
    )
    await callback_query.message.answer(f"Hi {user_name}, I am Yelan. You can send your ROM request by /request command.", reply_markup=keyboard)

# Request command
@dp.message_handler(commands=['request'])
async def cmd_request(message: types.Message):
    user_id = message.from_user.id

    # Check if the user has a cooldown
    if user_id in user_cooldowns and datetime.now() < user_cooldowns[user_id]:
        await message.answer("You need to wait before sending another request. Try again later.")
        return

    await message.answer("Which ROM are you requesting?")
    await dp.current_state().set_state('waiting_for_rom', user_id)

# Handle the user's ROM request input
@dp.message_handler(state='waiting_for_rom')
async def handle_rom_request(message: types.Message):
    user_id = message.from_user.id
    request_text = message.text

    # Create a request number (for simplicity, using random number here)
    request_number = random.randint(1000, 9999)

    # Forward the request to the admin group (GROUP_A_CHAT_ID)
    admin_message = f"New ROM request from {message.from_user.first_name} (@{message.from_user.username}):\n\nRequest: {request_text}\nRequest Number: {request_number}\nUser ID: {user_id}\nUsername: @{message.from_user.username}"
    await bot.forward_message(chat_id=GROUP_A_CHAT_ID, from_chat_id=message.chat.id, message_id=message.message_id)

    # Save the request to MongoDB
    requests_collection.insert_one({
        'user_id': user_id,
        'request_text': request_text,
        'request_number': request_number,
        'status': 'pending',
        'timestamp': datetime.now()
    })

    # Set a 24-hour cooldown for the user
    user_cooldowns[user_id] = datetime.now() + timedelta(hours=24)

    await message.answer(f"Your request has been sent to Admins. Your request number is: {request_number}")

# Track command
@dp.message_handler(commands=['track'])
async def cmd_track(message: types.Message):
    user_id = message.from_user.id
    request = requests_collection.find_one({'user_id': user_id, 'status': {'$ne': 'completed'}})

    if request:
        await message.answer(f"Your request number is {request['request_number']} and the status is {request['status']}.")
    else:
        await message.answer("No request sent.")

# Ping command
@dp.message_handler(commands=['ping'])
async def cmd_ping(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(f"Bot latency is {round(bot_info['telegram_id'])} ms.")

# Admin-only: Mark request as done
@dp.message_handler(commands=['done'])
async def cmd_done(message: types.Message):
    if message.from_user.id not in map(int, ADMIN_IDS):
        await message.answer("You are not authorized to use this command.")
        return

    try:
        request_number = int(message.get_args())
        request = requests_collection.find_one({'request_number': request_number})

        if request:
            requests_collection.update_one(
                {'request_number': request_number},
                {'$set': {'status': 'completed'}}
            )
            await message.answer(f"Request number {request_number} is marked as completed!")
        else:
            await message.answer(f"No request found with number {request_number}.")

    except ValueError:
        await message.answer("Please provide a valid request number.")

# Admin-only: Send a message to a user
@dp.message_handler(commands=['send'])
async def cmd_send(message: types.Message):
    if message.from_user.id not in map(int, ADMIN_IDS):
        await message.answer("You are not authorized to use this command.")
        return

    try:
        telegram_id = int(message.get_args())
        await bot.send_message(telegram_id, "Here is your requested ROM!")
        await message.answer(f"Message sent to {telegram_id}.")

    except ValueError:
        await message.answer("Please provide a valid Telegram ID.")

# Admin-only: Broadcast message
@dp.message_handler(commands=['broadcast'])
async def cmd_broadcast(message: types.Message):
    if message.from_user.id not in map(int, ADMIN_IDS):
        await message.answer("You are not authorized to use this command.")
        return

    text = message.get_args()
    users = requests_collection.find()

    for user in users:
        try:
            await bot.send_message(user['user_id'], text)
        except Exception as e:
            logging.error(f"Failed to send to {user['user_id']}: {e}")

    await message.answer(f"Broadcast sent to {len(users)} users.")

# Admin-only: Show DB details
@dp.message_handler(commands=['db'])
async def cmd_db(message: types.Message):
    if message.from_user.id not in map(int, ADMIN_IDS):
        await message.answer("You are not authorized to use this command.")
        return

    db_stats = {
        "Request Count": requests_collection.count_documents({}),
    }

    db_details = "\n".join([f"{key}: {value}" for key, value in db_stats.items()])
    await message.answer(f"Database Details:\n{db_details}")

# Webhook setup (to be used in Render)
async def on_start(request):
    return web.Response(text="Bot is running!")

if __name__ == '__main__':
    # Set up the webhook URL for Render
    app = web.Application()
    app.router.add_get('/', on_start)
    app.router.add_post(f'/{API_TOKEN}', dp.handle_update)

    # Run the bot with webhook
    web.run_app(app, host="0.0.0.0", port=int(os.getenv('PORT', 3000)))
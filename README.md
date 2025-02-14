# 🎮 Yelan - Pokémon ROM Finder Bot

**Yelan** is a **Telegram bot** designed to help users find Pokémon ROMs across multiple channels, request new ROMs, and stay updated with the latest uploads. It is built using **Python (aiogram)** and **MongoDB**, and optimized for deployment on **Render**.

---

## 🚀 Features

✅ **Find ROMs** (`/find <ROM Name>`)  
🔍 Searches in 7 pre-configured channels and provides a download link if found.  

✅ **Request a ROM** (`/request`)  
📩 Allows users to request a ROM that isn't found in the channels. (24-hour cooldown)  

✅ **Latest Uploads** (`/latest`)  
📥 Displays the **5 most recent ROMs** uploaded across the channels.  

✅ **Featured ROMs** (`/featured`)  
⭐ Shows **handpicked ROMs** that are either popular or newly released.  

✅ **ROM Popularity Tracker** (`/trending`)  
🔥 Tracks the most searched/downloaded ROMs in the past week/month.  

✅ **Inline Buttons**  
📌 When users start the bot (`/start`), they get two inline buttons:  
   - **Help ℹ️** → Displays available commands.  
   - **About Me 🤗** → Shows owner & creator details.  

✅ **Cancel Ongoing Actions** (`/cancel`)  
❌ Stops any `/find` or `/request` process in progress.  

✅ **Bot Status Check** (`/ping`)  
📡 Ensures the bot is active and responsive.  

✅ **Hidden Help Command** (`/help_link`)  
🔗 Provides direct command links (not listed in `/help`).  

✅ **Fun Easter Eggs**  
🎭 `/mystery` - Sends a random Pokémon fact or joke.  
✨ `/shinyhunt` - Sends a random Shiny Pokémon image.  

---

## 🛠 Installation & Deployment

### **1️⃣ Clone the Repository**
sh
`git clone https://github.com/aapokepikachu/Yelan.git
cd yelan-bot`

### **2️⃣ Install Dependencies**

`pip install -r requirements.txt`

### **3️⃣ Set Up Environment Variables**

Create a .env file in the project root and add:

BOT_TOKEN=your_telegram_bot_token
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/yelan_bot
ADMIN_GROUP_ID=-1001234567890
CHANNEL_IDS=-1001111111111,-1002222222222,-1003333333333,-1004444444444,-1005555555555,-1006666666666,-1007777777777


---

## 🚀 Running the Bot

*Local Development*

Run the bot using:

`python bot.py`

*Deploy on Render*

1️⃣ Push the project to GitHub
2️⃣ Create a Render Web Service
3️⃣ Set up Environment Variables
4️⃣ Deploy & Enjoy! 🎮


---

## 🤝 Credits

👤 Owner: @AAPoke
🛠 Creator: @PokemonBots
💰 Monetization: @PokemonNdsGba



---

## 📜 License

This project is open-source and available under the MIT License.

---

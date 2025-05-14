import re
import asyncio
import logging
from datetime import datetime, timedelta

from pymongo import MongoClient
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import (
    API_ID,
    API_HASH,
    MONGO_DB_URI,
    OWNER_ID,
    HELPERS,
    JOIN_CHAT,
    SUPPORT_CHATID,
    STORAGE_CHANNELID,
    QR_IMAGE_URL,
    pyrecordcn
)

from Elapsed import app as bot

logging.basicConfig(level=logging.INFO)

mongo_client = MongoClient(MONGO_DB_URI)
mongo_db = mongo_client["Elapsed"]
payments_collection = mongo_db["payments"]
cloned_bots_collection = mongo_db["userbotdb"]
settings_collection = mongo_db["settings"]

DURATIONS = {
    "half_month": {"days": 15, "amount": 35},
    "one_month": {"days": 30, "amount": 50},
    "two_month": {"days": 60, "amount": 100},
}

async def is_userbot_stopped():
    settings = settings_collection.find_one({"_id": "userbot_status"})
    return settings and settings.get("stopped", False)

async def restart_bots():
    if await is_userbot_stopped():
        logging.info("UserBots are globally stopped. Skipping restart.")
        return

    bots = list(cloned_bots_collection.find())
    for bot_data in bots:
        user_id = bot_data["user_id"]
        string = bot_data["string"]
        user_name = bot_data.get("name", "Unknown")

        try:
            ai = Client(
                name=f"restart-{user_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=string,
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.start()
            await ai.join_chat(JOIN_CHAT)
            await ai.send_message("me", "UserBot restarted successfully.")
            await ai.stop()
        except Exception as e:
            logging.warning(f"Dead/invalid session for user {user_id}: {e}")
            cloned_bots_collection.delete_one({"user_id": user_id})

            for admin_id in HELPERS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ ᴅᴇᴀᴅ ꜱᴇꜱꜱɪᴏɴ ᴅᴇᴛᴇᴄᴛᴇᴅ ᴀɴᴅ ʀᴇᴍᴏᴠᴇᴅ.\nᴜꜱᴇʀ: {user_name}\nUser ɪᴅ: {user_id}\nᴇʀʀᴏʀ: {str(e)}"
                    )
                except:
                    pass

            try:
                await bot.send_message(
                    user_id,
                    "ʏᴏᴜʀ ᴜꜱᴇʀʙᴏᴛ ꜱᴇꜱꜱɪᴏɴ ᴀᴘᴘᴇᴀʀꜱ ᴛᴏ ʙᴇ ʀᴇᴍᴏᴠᴇᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ..\nᴘʟᴇᴀꜱᴇ ʀᴇ - ᴄʟᴏɴᴇ ᴜꜱɪɴɢ /clone <your_string> ."
                )
            except:
                pass

# ------------------ Stop All Client ------------------

@bot.on_message(filters.command("stopallub") & filters.user(HELPERS))
async def stop_all_clients(client, message: Message):
    settings_collection.update_one(
        {"_id": "userbot_status"},
        {"$set": {"stopped": True}},
        upsert=True
    )
    await message.reply_text("ᴀʟʟ ᴜꜱᴇʀʙᴏᴛ ꜱᴇꜱꜱɪᴏɴꜱ ʜᴀᴠᴇ ʙᴇᴇɴ ꜰᴏʀᴄᴇꜰᴜʟʟʏ ꜱᴛᴏᴘᴘᴇᴅ ʙʏ ᴍᴏᴅᴇʀᴀᴛᴏʀꜱ .")
    users = payments_collection.find({"status": "approved"})
    for user in users:
        try:
            await client.send_message(user["user_id"], "ᴜꜱᴇʀʙᴏᴛ ꜱᴇʀᴠɪᴄᴇ ʜᴀꜱ ʙᴇᴇɴ ᴛᴇᴍᴘᴏʀᴀʀɪʟʏ ᴘᴀᴜꜱᴇᴅ ʙʏ ᴍᴏᴅᴇʀᴀᴛᴏʀꜱ .")
        except:
            pass
# ------------------ Restart All Client ------------------

@bot.on_message(filters.command("rsallub") & filters.user(HELPERS))
async def restart_all_clients(client, message: Message):
    status = await is_userbot_stopped()
    if status:
        settings_collection.update_one({"_id": "userbot_status"}, {"$set": {"stopped": False}}, upsert=True)
        await message.reply_text("ᴜꜱᴇʀʙᴏᴛ ꜱᴇʀᴠɪᴄᴇ ɪꜱ ɴᴏᴡ ʀᴇꜱᴜᴍᴇᴅ, ʀᴇꜱᴛᴀʀᴛɪɴɢ ᴀʟʟ ᴄʟɪᴇɴᴛꜱ.....")
        users = payments_collection.find({"status": "approved"})
        for user in users:
            try:
                await client.send_message(user["user_id"], "ᴜꜱᴇʀʙᴏᴛ ꜱᴇʀᴠɪᴄᴇ ɪꜱ ɴᴏᴡ ᴀᴄᴛɪᴠᴇ ᴀɢᴀɪɴ.")
            except:
                pass
    else:
        await message.reply_text("ʀᴇꜱᴛᴀʀᴛɪɴɢ ᴀʟʟ ᴜꜱᴇʀʙᴏᴛ ꜱᴇꜱꜱɪᴏɴꜱ...")
        users = payments_collection.find({"status": "approved"})
        for user in users:
            try:
                await client.send_message(user["user_id"], "ᴜꜱᴇʀʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛɪɴɢ, ɪᴛ ᴡɪʟʟ ʙᴇ ʙᴀᴄᴋ ɪɴ ᴀ ꜰᴇᴡ ꜱᴇᴄᴏɴᴅꜱ..")
            except:
                pass

    await restart_bots()

    if not status:
        users = payments_collection.find({"status": "approved"})
        for user in users:
            try:
                await client.send_message(user["user_id"], "ᴜꜱᴇʀʙᴏᴛ ʀᴇʙᴏᴏᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ. ʙᴀᴄᴋ ᴏɴʟɪɴᴇ.")
            except:
                pass

# ------------------ Start Personal Client ------------------

@bot.on_message(filters.command("startub") & filters.private)
async def start_userbot(client, message: Message):
    user_id = message.from_user.id
    if await is_userbot_stopped():
        await message.reply_text("ᴜꜱᴇʀʙᴏᴛ ᴀᴄᴛɪᴏɴꜱ ᴀʀᴇ ᴛᴇᴍᴘᴏʀᴀʀɪʟʏ ᴅɪꜱᴀʙʟᴇᴅ ʙʏ  ᴍᴏᴅᴇʀᴀᴛᴏʀꜱ .")
        return

    user_data = payments_collection.find_one({"user_id": user_id, "status": "approved"})
    if not user_data:
        await message.reply_text("ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀɴ ᴀᴘᴘʀᴏᴠᴇᴅ ꜱᴜʙꜱᴄʀɪʙᴇʀ. ᴜꜱᴇ /Clone ᴀꜰᴛᴇʀ ɢᴇᴛᴛɪɴɢ ᴀᴘᴘʀᴏᴠᴇᴅ.")
        return

    ub_data = cloned_bots_collection.find_one({"user_id": user_id})
    if not ub_data:
        await message.reply_text("ɴᴏ ᴜꜱᴇʀʙᴏᴛ ꜱᴇꜱꜱɪᴏɴ ꜰᴏᴜɴᴅ, ᴜꜱᴇ /Clone <ꜱᴛʀɪɴɢ> ᴛᴏ ꜱᴛᴀʀᴛ.")
        return

    try:
        ai = Client(
            name=f"startub-{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=ub_data["string"],
            plugins={"root": "Elapsed.plugins.userbot"},
        )
        await ai.start()
        await ai.join_chat(JOIN_CHAT)
        await ai.send_message("me", "UserBot restarted with /startub.")
        await ai.stop()
        await message.reply_text("ʏᴏᴜʀ ᴜꜱᴇʀʙᴏᴛ ʜᴀꜱ ʙᴇᴇɴ ʀᴇꜱᴛᴀʀᴛᴇᴅ. ᴛʏᴘᴇ .help ɪɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ᴛᴏ ʙᴇɢɪɴ, ɪꜰ ɴᴏᴛʜɪɴɢ ꜱʜᴏᴡ ᴜᴘ ᴛʏᴘᴇ /startub")
    except Exception as e:
        logging.exception(f"Failed to restart UB via /startub: {e}")
        await message.reply_text("ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ꜱᴇꜱꜱɪᴏɴ ᴏʀ ᴄᴏɴᴛᴀᴄᴛ  ᴍᴏᴅᴇʀᴀᴛᴏʀꜱ.")

# ------------------ Clone Client ------------------

@bot.on_message(filters.command("clone") & filters.private)
async def start_clone_flow(client, message: Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    if len(message.command) > 1:
        string_token = message.command[1]
        payment_data = payments_collection.find_one({"user_id": user_id, "status": "approved"})
        if not payment_data:
            await message.reply_text("ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴘᴘʀᴏᴠᴇᴅ ʏᴇᴛ. ᴘʟᴇᴀꜱᴇ ᴘᴀʏ ᴀɴᴅ ᴡᴀɪᴛ ꜰᴏʀ ᴀᴘᴘʀᴏᴠᴀʟ ʙᴇꜰᴏʀᴇ ᴄʟᴏɴɪɴɢ.")
            return

        bots = list(cloned_bots_collection.find())
        for bot_entry in bots:
            if bot_entry['string'] == string_token:
                await message.reply_text("ᴛʜɪꜱ ᴀꜱꜱɪꜱᴛᴀɴᴛ ᴜꜱᴇʀʙᴏᴛ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴄʟᴏɴᴇᴅ, ᴜꜱᴇ /startun ɪꜰ ɪᴛ'ꜱ ᴏꜰꜰ.")
                return

        ai = Client(
            f"{name}",
            API_ID,
            API_HASH,
            session_string=string_token,
            plugins={"root": "Elapsed.plugins.userbot"},
        )
        try:
            await ai.start()
            await ai.join_chat(JOIN_CHAT)
            bot_user = await ai.get_me()

            approver_info = payment_data.get("approver", "Unknown")

            details = {
                'is_bot': False,
                'user_id': user_id,
                'name': bot_user.first_name,
                'string': string_token,
                'username': bot_user.username,
                'cloned_at': datetime.utcnow()
            }
            cloned_bots_collection.insert_one(details)

            log_text = (
                f"ᴜꜱᴇʀ ᴄʟᴏɴᴇᴅ ᴜʙ:\n"
                f"ɴᴀᴍᴇ: {bot_user.first_name}\n"
                f"ᴜꜱᴇʀ ɪᴅ: {user_id}\n"
                f"ᴜꜱᴇʀɴᴀᴍᴇ: @{bot_user.username or 'N/A'}\n"
                f"ᴅᴄ ɪᴅ: {message.from_user.dc_id}\n"
                f"ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ: {approver_info}\n"
                f"ɴᴀᴍᴇ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (IST)"
            )
            log_msg = await client.send_message(STORAGE_CHANNELID, log_text)
            payments_collection.update_one({"user_id": user_id}, {"$set": {"clone_log_id": log_msg.id}})

            await message.reply_text(f"ᴄʟᴏɴᴇᴅ ᴜʙ @{bot_user.username or 'N/A'}. ᴜꜱᴇ /startub to activate. ꜰᴏʀ ʜᴇʟᴘ, ᴛʏᴘᴇ .help")
        except Exception as e:
            logging.exception(f"Error while cloning ub: {e}")
            await message.reply_text(f"ᴇʀʀᴏʀ ᴅᴜʀɪɴɢ ᴄʟᴏɴɪɴɢ: {e}")
        return

    payment_data = payments_collection.find_one({"user_id": user_id, "status": "approved"})
    if payment_data:
        await message.reply_text("ʏᴏᴜ'ʀᴇ ᴀʟʀᴇᴀᴅʏ ᴀᴘᴘʀᴏᴠᴇᴅ, ꜱᴇɴᴅ /clone <ꜱᴛʀɪɴɢ> ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ʜᴀʟꜰ ᴍᴏɴᴛʜ ", callback_data="pay_half_month")],
        [
            InlineKeyboardButton("1 ᴍᴏɴᴛʜ", callback_data="pay_one_month"),
            InlineKeyboardButton("2 ᴍᴏɴᴛʜ ", callback_data="pay_two_month")
        ]
    ])
    await message.reply_text("35 ꜰᴏʀ ʜᴀʟꜰ, 50 ꜰᴏʀ 1 ᴍᴏɴᴛʜ & 100 ꜰᴏʀ 2 ᴍᴏɴᴛʜ, ᴄʜᴏᴏꜱᴇ ᴜʀ ᴘʟᴀɴ ᴀᴄᴄᴏʀᴅɪɴɢʟʏ :", reply_markup=keyboard)


@bot.on_callback_query(filters.regex(r"pay_(half_month|one_month|two_month)"))
async def handle_payment_selection(client, query: CallbackQuery):
    user_id = query.from_user.id
    duration_key = query.data.replace("pay_", "")
    duration_data = DURATIONS[duration_key]

    payments_collection.update_one({"user_id": user_id}, {
        "$set": {
            "user_id": user_id,
            "duration_key": duration_key,
            "amount": duration_data["amount"],
            "days": duration_data["days"],
            "status": "pending",
            "start_time": datetime.utcnow()
        }
    }, upsert=True)

    await query.message.delete()
    await query.message.reply_photo(
        QR_IMAGE_URL,
        caption=f"ꜱᴇɴᴅ ᴛʜᴇ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ᴏꜰ ʏᴏᴜʀ ₹{duration_data['amount']} ᴘᴀʏᴍᴇɴᴛ ʜᴇʀᴇ ᴡɪᴛʜɪɴ 3 ᴍɪɴᴜᴛᴇꜱ."
    )

    await asyncio.sleep(180)
    pending = payments_collection.find_one({"user_id": user_id, "status": "pending"})
    if pending:
        payments_collection.delete_one({"user_id": user_id})
        try:
            await client.send_message(user_id, "ᴛɪᴍᴇ ᴇxᴘɪʀᴇᴅ, ᴘʟᴇᴀꜱᴇ ꜱᴛᴀʀᴛ ᴀɢᴀɪɴ ᴜꜱɪɴɢ /clone..")
        except:
            pass


@bot.on_message(filters.private & filters.photo)
async def handle_payment_screenshot(client, message: Message):
    user_id = message.from_user.id
    pending = payments_collection.find_one({"user_id": user_id, "status": "pending"})
    if not pending:
        await message.reply_text("ɴᴏ ᴘᴇɴᴅɪɴɢ ᴘᴀʏᴍᴇɴᴛ ꜰᴏᴜɴᴅ. ꜱᴛᴀʀᴛ ᴡɪᴛʜ /clone.")
        return

    payments_collection.update_one({"user_id": user_id}, {"$set": {"status": "verifying"}})

    user = message.from_user
    duration_data = DURATIONS[pending["duration_key"]]
    text = (
        f"ɴᴀᴍᴇ: {user.first_name}\n"
        f"ᴜꜱᴇʀ ɪᴅ : {user.id}\n"
        f"ᴜꜱᴇʀɴᴀᴍᴇ : @{user.username or 'N/A'}\n"
        f":ᴅᴄ ɪᴅ {user.dc_id}\n"
        f":ᴅᴜʀᴀᴛɪᴏɴ  {duration_data['days']} ᴅᴀʏꜱ"
    )

    for admin_id in HELPERS:
        try:
            await client.send_photo(admin_id, message.photo.file_id, caption=text)
        except Exception as e:
            logging.warning(f"Couldn't send screenshot to {admin_id}: {e}")

    support_text = text + "\n\nᴍᴏᴅᴇʀᴀᴛᴏʀꜱ ᴀᴜᴛʜᴏʀɪꜱᴇ ᴏɴʟʏ :"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴀᴘᴘʀᴏᴠᴇ ", callback_data=f"approve{user_id}"),
            InlineKeyboardButton("ᴅᴇᴄʟɪɴᴇ ", callback_data=f"decline{user_id}")
        ]
    ])
    await client.send_message(SUPPORT_CHATID, support_text, reply_markup=keyboard)
    await message.reply_text("ʏᴏᴜʀ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ʜᴀꜱ ʙᴇᴇɴ ꜱᴜʙᴍɪᴛᴛᴇᴅ. ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜰᴏʀ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ.")


@bot.on_callback_query(filters.regex(r"(approve|decline)\d+"))
async def handle_approval_decision(client, query: CallbackQuery):
    match = re.match(r"(approve|decline)(\d+)", query.data)
    if not match:
        await query.answer("Invalid action.")
        return

    if query.from_user.id not in HELPERS:
        await query.answer("You're not authorized to perform this action.", show_alert=True)
        return

    action, user_id = match.groups()
    user_id = int(user_id)

    user_data = payments_collection.find_one({"user_id": user_id})
    if not user_data:
        await query.answer("User data not found or already processed.", show_alert=True)
        return

    if action == "decline":
        payments_collection.delete_one({"user_id": user_id})
        await client.send_message(user_id, "ʏᴏᴜʀ ʀᴇQᴜᴇꜱᴛ ᴛᴏ ᴄʟᴏɴᴇ ʜᴀꜱ ʙᴇᴇɴ ᴅᴇᴄʟɪɴᴇᴅ, ᴄᴏɴᴛᴀᴄᴛ ꜱᴜᴘᴘᴏʀᴛ .")
        await query.message.edit_text("ᴄʟᴏɴɪɴɢ ʀᴇQᴜᴇꜱᴛ ᴅᴇᴄʟɪɴᴇᴅ 💢.")
    else:
        expire_time = datetime.utcnow() + timedelta(days=user_data["days"])
        approver_info = f"{query.from_user.first_name} (@{query.from_user.username or 'N/A'})"
        payments_collection.update_one({"user_id": user_id}, {
            "$set": {
                "status": "approved",
                "approved_at": datetime.utcnow(),
                "expire_at": expire_time,
                "approver": approver_info
            }
        })
        await client.send_message(user_id, "ᴄʟᴏɴɪɴɢ ʀᴇQᴜᴇꜱᴛ ᴀᴘᴘʀᴏᴠᴇᴅ, ʏᴏᴜ ᴍᴀʏ ɴᴏᴡ ꜱᴇɴᴅ /ᴄʟᴏɴᴇ <ʏᴏᴜʀ_ꜱᴛʀɪɴɢ> ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ.")
        
        await client.send_message(pyrecordcn, f"#NewPaymentCR\n\n"
                                              f"ɴᴀᴍᴇ: {query.from_user.first_name}\n"
                                              f"ᴜꜱᴇʀ ɪᴅ: {user_id}\n"
                                              f"ᴅᴜʀᴀᴛɪᴏɴ : {user_data['days']} ᴅᴀʏꜱ\n"
                                              f"ᴘʟᴀɴ: ₹{user_data['amount']}")
        
        log_text = (
            f"ᴄʟᴏɴɪɴɢ ᴀᴘᴘʀᴏᴠᴇᴅ \n"
            f"ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ: {approver_info}\n"
            f"ᴜꜱᴇʀ ɪᴅ: {user_id}\n"
            f"ᴅᴜʀᴀᴛɪᴏɴ : {user_data['days']} ᴅᴀʏꜱ\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (IST)"
        )
        log_msg = await client.send_message(STORAGE_CHANNELID, log_text)
        payments_collection.update_one({"user_id": user_id}, {"$set": {"log_msg_id": log_msg.id}})
        await query.message.edit_text("ᴄʟᴏɴɪɴɢ ʀᴇQᴜᴇꜱᴛ ᴀᴘᴘʀᴏᴠᴇᴅ.")
        

async def monthly_summary_task():
    while True:
        now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        last_day = calendar.monthrange(now.year, now.month)[1]
        midnight = datetime(now.year, now.month, last_day, 23, 59, 59)
        wait_seconds = (midnight - now).total_seconds()
        await asyncio.sleep(max(wait_seconds, 0))

        start = datetime(now.year, now.month, 1)
        end = datetime(now.year, now.month, last_day, 23, 59, 59)

        payments = payments_collection.find({
            "status": "approved",
            "approved_at": {"$gte": start, "$lte": end}
        })

        total = sum(p.get("amount", 0) for p in payments)
        month_name = now.strftime("%B")

        await bot.send_message(pyrecordcn,
                               f"#MonthlySummary\n\n"
                               f"Month: {month_name}\n"
                               f"Period: 1st to {last_day}\n"
                               f"Total Revenue: ₹{total}\n"
                               f"Total Profit: ₹{total}")

        await asyncio.sleep(90)


async def main():
    await bot.start()
    asyncio.create_task(monthly_summary_task())

# ------------------ Quit UserBot ------------------

@bot.on_message(filters.command("quiteub") & filters.private)
async def quit_userbot(client, message: Message):
    user_id = message.from_user.id

    ub_data = cloned_bots_collection.find_one({"user_id": user_id})
    if not ub_data:
        await message.reply_text("No UserBot session found to quit.")
        return

    cloned_bots_collection.delete_one({"user_id": user_id})
    await message.reply_text("Your UserBot session has been successfully removed. You can /clone again anytime.")
    
    for admin_id in HELPERS:
        try:
            await client.send_message(
                admin_id,
                f"User {message.from_user.first_name} (ID: {user_id}) has quit their UserBot session."
            )
        except:
            pass

# ------------------ Expelle Client ------------------

@bot.on_message(filters.command("terminate") & filters.user(HELPERS))
async def manage_user(client, message: Message):
    args = message.text.split(maxsplit=2)
    user = None
    user_id = None
    name = None

    if message.reply_to_message:
        user = message.reply_to_message.from_user
    elif len(args) == 3 and args[2].isdigit():
        try:
            user_id = int(args[2])
            user = await client.get_users(user_id)
        except:
            await message.reply_text("Invalid user ID or user not found.")
            return
    else:
        await message.reply_text("Reply to a user or use /terminate username user_id.")
        return

    user_id = user.id
    name = user.first_name

    subscription = payments_collection.find_one({"user_id": user_id, "status": "approved"})
    if not subscription:
        await message.reply_text(f"{name} ({user_id}) does not have an active subscription.")
        return

    cloned = cloned_bots_collection.find_one({"user_id": user_id})

    buttons = []
    if cloned:
        buttons.extend([
            [InlineKeyboardButton("Terminate Sessions", callback_data=f"terminate_ub_{user_id}")],
            [InlineKeyboardButton("Terminate Subscription", callback_data=f"terminate_sub_{user_id}")],
            [InlineKeyboardButton("Terminate All", callback_data=f"terminate_all_{user_id}")]
        ])
    else:
        buttons.append([InlineKeyboardButton("Terminate Subscription", callback_data=f"terminate_sub_{user_id}")])

    buttons.append([InlineKeyboardButton("Cancel", callback_data="cancel_manage")])

    markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        f"What do you want to do with {name} ({user_id})?",
        reply_markup=markup
    )


@bot.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in HELPERS:
        return await callback_query.answer("You are not authorized to use this.", show_alert=True)

    data = callback_query.data
    target_id = int(data.split("_")[-1])
    try:
        target_user = await client.get_users(target_id)
        name = target_user.first_name
    except:
        name = "Unknown"

    if data.startswith("terminate_ub_"):
        cloned_bots_collection.delete_one({"user_id": target_id})
        await callback_query.answer(f"Cloned session for {name} ({target_id}) terminated.", show_alert=True)
        await callback_query.edit_message_text(f"Cloned session for {name} ({target_id}) terminated.")
        try:
            await client.send_message(target_id, "Your cloned session has been terminated by the admin.")
        except:
            pass

    elif data.startswith("terminate_sub_"):
        sub = payments_collection.find_one({"user_id": target_id})
        if sub and "log_msg_id" in sub:
            try:
                await bot.delete_messages(STORAGE_CHANNELID, message_ids=[sub["log_msg_id"]])
            except:
                pass
        payments_collection.delete_one({"user_id": target_id})
        await callback_query.answer(f"Subscription for {name} ({target_id}) terminated.", show_alert=True)
        await callback_query.edit_message_text(f"Subscription for {name} ({target_id}) terminated.")
        try:
            await client.send_message(target_id, "Your subscription has been terminated by the admin.")
        except:
            pass

    elif data.startswith("terminate_all_"):
        cloned_bots_collection.delete_one({"user_id": target_id})
        sub = payments_collection.find_one({"user_id": target_id})

        if sub and "log_msg_id" in sub:
            try:
                await bot.delete_messages(STORAGE_CHANNELID, message_ids=[sub["log_msg_id"]])
            except:
                pass

        if sub and "clone_log_id" in sub:
            try:
                original_msg = await bot.get_messages(STORAGE_CHANNELID, sub["clone_log_id"])
                terminated_by = f"\nTerminated by: {callback_query.from_user.first_name} (@{callback_query.from_user.username or 'N/A'})"
                updated_text = original_msg.text + terminated_by
                await bot.edit_message_text(STORAGE_CHANNELID, sub["clone_log_id"], updated_text)
            except:
                pass

        payments_collection.delete_one({"user_id": target_id})
        await callback_query.answer(f"All data for {name} ({target_id}) has been terminated.", show_alert=True)
        await callback_query.edit_message_text(f"All data for {name} ({target_id}) has been terminated.")
        try:
            await client.send_message(target_id, "All your data including subscription and sessions have been terminated by the admin.")
        except:
            pass

    elif data == "cancel_manage":
        await callback_query.answer("Operation cancelled.", show_alert=True)
        await callback_query.edit_message_text("Operation cancelled.")

# ------------------ All Client Info ------------------

@bot.on_message(filters.command("allclient") & filters.user(HELPERS))
async def all_clients_info(client, message: Message):
    active_clients = list(payments_collection.find({"status": "approved"}))
    total_clients = len(active_clients)

    if total_clients == 0:
        await message.reply_text("No active clients at the moment.")
        return

    lines = [f"**Total Active Clients: {total_clients}**\n"]

    for idx, client_data in enumerate(active_clients, 1):
        user_id = client_data["user_id"]
        expire_at = client_data.get("expire_at")
        name = "Unknown"

        try:
            user = await client.get_users(user_id)
            name = user.first_name
        except:
            pass

        if expire_at:
            remaining = expire_at - datetime.utcnow()
            days = remaining.days
            hours = remaining.seconds // 3600
            time_left = f"{days} days, {hours} hours left"
        else:
            time_left = "Unknown duration"

        lines.append(f"**{idx}) {name}** (`{user_id}`)\n`{time_left}`\n")

    output = "\n".join(lines)
    await message.reply_text(output, disable_web_page_preview=True)

# ------------------ Main Code Script ------------------

async def check_expired_access():
    while True:
        now = datetime.utcnow()
        expired = payments_collection.find({"status": "approved", "expire_at": {"$lte": now}})
        for user in expired:
            try:
                if "log_msg_id" in user:
                    await bot.delete_messages(STORAGE_CHANNELID, message_ids=[user["log_msg_id"]])
            except:
                pass
            payments_collection.delete_one({"user_id": user["user_id"]})
        await asyncio.sleep(3600)


async def main():
    await bot.start()
    asyncio.create_task(check_expired_access())
    print("Bot is running...")
    await idle()


if __name__ == "__main__":
    asyncio.run(main())

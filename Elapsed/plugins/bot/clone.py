import re
import asyncio
import logging
from datetime import datetime, timedelta

from pymongo import MongoClient
from Elapsed.misc import SUDOERS

from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from config import (
    API_ID,
    API_HASH,
    MONGO_DB_URI,
    OWNER_ID,
    JOIN_CHAT,
    SUPPORT_CHATID,
    STORAGE_CHANNELID,
    QR_IMAGE_URL
)

from Elapsed import app as bot

logging.basicConfig(level=logging.INFO)

mongo_client = MongoClient(MONGO_DB_URI)
mongo_db = mongo_client["Elapsed"]
payments_collection = mongo_db["payments"]
cloned_bots_collection = mongo_db["userbotdb"]

DURATIONS = {
    "half_month": {"days": 15, "amount": 35},
    "one_month": {"days": 30, "amount": 50},
    "two_month": {"days": 60, "amount": 100},
}


async def restart_bots():
    bots = list(cloned_bots_collection.find())
    for bot in bots:
        try:
            ai = Client(
                name=f"restart-{bot['user_id']}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=bot['string'],
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.start()
            await ai.join_chat(JOIN_CHAT)
            await ai.send_message("me", "UserBot restarted successfully.")
            await ai.stop()
        except Exception as e:
            logging.exception(f"Failed to restart userbot for {bot['user_id']}: {e}")


@bot.on_message(filters.command("clone") & filters.private)
async def start_clone_flow(client, message: Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    if len(message.command) > 1:
        string_token = message.command[1]
        payment_data = payments_collection.find_one({"user_id": user_id, "status": "approved"})
        if not payment_data:
            await message.reply_text("You are not approved yet. Please pay and wait for approval before cloning.")
            return

        bots = list(cloned_bots_collection.find())
        for bot_entry in bots:
            if bot_entry['string'] == string_token:
                await message.reply_text("This Assistant UserBot is already cloned. Use /startub if it's off.")
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
                f"User Cloned UB:\n"
                f"Name: {bot_user.first_name}\n"
                f"User ID: {user_id}\n"
                f"Username: @{bot_user.username if bot_user.username else 'N/A'}\n"
                f"DC ID: {message.from_user.dc_id}\n"
                f"Approved By: {approver_info}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (IST)"
            )
            log_msg = await client.send_message(STORAGE_CHANNELID, log_text)
            payments_collection.update_one({"user_id": user_id}, {"$set": {"clone_log_id": log_msg.id}})

            await message.reply_text(f"Cloned UB @{bot_user.username or 'N/A'}. Use `.start` to activate. For help, type `.help`")
        except Exception as e:
            logging.exception(f"Error while cloning ub: {e}")
            await message.reply_text(f"Error during cloning: {e}")
        return

    payment_data = payments_collection.find_one({"user_id": user_id, "status": "approved"})
    if payment_data:
        await message.reply_text("You're already approved. Send /clone <string> to proceed.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Half month - ₹35", callback_data="pay_half_month")],
        [
            InlineKeyboardButton("1 month - ₹50", callback_data="pay_one_month"),
            InlineKeyboardButton("2 month - ₹100", callback_data="pay_two_month")
        ]
    ])
    await message.reply_text("Choose your duration and pay accordingly:", reply_markup=keyboard)


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
        caption=f"Send the screenshot of your ₹{duration_data['amount']} payment here within 3 minutes."
    )

    await asyncio.sleep(180)
    pending = payments_collection.find_one({"user_id": user_id, "status": "pending"})
    if pending:
        payments_collection.delete_one({"user_id": user_id})
        try:
            await client.send_message(user_id, "Time expired. Please start again using /clone.")
        except:
            pass


@bot.on_message(filters.private & filters.photo)
async def handle_payment_screenshot(client, message: Message):
    user_id = message.from_user.id
    pending = payments_collection.find_one({"user_id": user_id, "status": "pending"})
    if not pending:
        await message.reply_text("No pending payment found. Start with /clone.")
        return

    payments_collection.update_one({"user_id": user_id}, {"$set": {"status": "verifying"}})

    user = message.from_user
    duration_data = DURATIONS[pending["duration_key"]]
    text = (
        f"Name: {user.first_name}\n"
        f"User ID: {user.id}\n"
        f"Username: @{user.username if user.username else 'N/A'}\n"
        f"DC ID: {user.dc_id}\n"
        f"Duration: {duration_data['days']} days"
    )

    for admin_id in list(set(SUDOERS + [OWNER_ID])):
        try:
            await client.send_photo(admin_id, message.photo.file_id, caption=text)
        except Exception as e:
            logging.warning(f"Couldn't send screenshot to {admin_id}: {e}")

    support_text = text + "\n\nApprove or decline the payment:"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve{user_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline{user_id}")
        ]
    ])
    await client.send_message(SUPPORT_CHATID, support_text, reply_markup=keyboard)
    await message.reply_text("Your screenshot has been submitted. Please wait for verification.")


@bot.on_callback_query(filters.regex(r"(approve|decline)\d+"))
async def handle_approval_decision(client, query: CallbackQuery):
    match = re.match(r"(approve|decline)(\d+)", query.data)
    if not match:
        await query.answer("Invalid action.")
        return

    if query.from_user.id not in SUDOERS and query.from_user.id != OWNER_ID:
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
        await client.send_message(user_id, "Your payment was declined. Contact support if needed.")
        await query.message.edit_text("❌ Payment declined.")
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

        await client.send_message(user_id, "Payment approved! You may now send /clone <your_string> to proceed.")

        log_text = (
            f"Cloning Approved\n"
            f"Approved By: {approver_info}\n"
            f"User ID: {user_id}\n"
            f"Duration: {user_data['days']} days\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (IST)"
        )
        log_msg = await client.send_message(STORAGE_CHANNELID, log_text)
        payments_collection.update_one({"user_id": user_id}, {"$set": {"log_msg_id": log_msg.id}})
        await query.message.edit_text("✅ Payment approved.")


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


@bot.on_message(filters.command("terminate") & filters.user(SUDOERS + [OWNER_ID]))
async def terminate_user(client, message: Message):
    user = None
    user_id = None
    name = None

    if message.reply_to_message:
        user = message.reply_to_message.from_user
        user_id = user.id
        name = user.first_name
    elif len(message.command) >= 2:
        identifier = message.command[1]
        if identifier.startswith("@"):
            try:
                user = await client.get_users(identifier)
                user_id = user.id
                name = user.first_name
            except:
                await message.reply_text("User not found.")
                return
        else:
            try:
                user_id = int(identifier)
                user = await client.get_users(user_id)
                name = user.first_name
            except:
                await message.reply_text("Invalid user ID.")
                return
    else:
        await message.reply_text("Reply to a user or provide their ID/username.\nUsage: `/terminate <user_id or @username>`", parse_mode="markdown")
        return

    bot_entry = cloned_bots_collection.find_one({"user_id": user_id})
    if not bot_entry:
        await message.reply_text(f"{name} ({user_id}) is not part of any active UB.")
        return

    cloned_bots_collection.delete_one({"user_id": user_id})

    try:
        await client.send_message(user_id, "You have been terminated from the service.")
    except:
        pass

    await message.reply_text(f"✅ {name} ({user_id}) has been terminated from UB.")
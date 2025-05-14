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
    QR_IMAGE_URL
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
                        f"⚠️ Dead session detected and removed.\nUser: {user_name}\nUser ID: {user_id}\nError: {str(e)}"
                    )
                except:
                    pass

            try:
                await bot.send_message(
                    user_id,
                    "Your UserBot session appears to be removed or expired.\nPlease re-clone using `/clone <your_string>`."
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
    await message.reply_text("All UserBot sessions have been forcefully stopped.")
    users = payments_collection.find({"status": "approved"})
    for user in users:
        try:
            await client.send_message(user["user_id"], "UserBot service has been temporarily paused by admin.")
        except:
            pass
# ------------------ Restart All Client ------------------

@bot.on_message(filters.command("rsallub") & filters.user(HELPERS))
async def restart_all_clients(client, message: Message):
    status = await is_userbot_stopped()
    if status:
        settings_collection.update_one({"_id": "userbot_status"}, {"$set": {"stopped": False}}, upsert=True)
        await message.reply_text("UserBot service is now resumed. Restarting all clients...")
        users = payments_collection.find({"status": "approved"})
        for user in users:
            try:
                await client.send_message(user["user_id"], "UserBot service is now active again.")
            except:
                pass
    else:
        await message.reply_text("Rebooting all UserBot sessions...")
        users = payments_collection.find({"status": "approved"})
        for user in users:
            try:
                await client.send_message(user["user_id"], "UserBot is rebooting. It will be back in a few seconds.")
            except:
                pass

    await restart_bots()

    if not status:
        users = payments_collection.find({"status": "approved"})
        for user in users:
            try:
                await client.send_message(user["user_id"], "UserBot reboot completed. Back online.")
            except:
                pass

# ------------------ Start Personal Client ------------------

@bot.on_message(filters.command("startub") & filters.private)
async def start_userbot(client, message: Message):
    user_id = message.from_user.id
    if await is_userbot_stopped():
        await message.reply_text("UserBot actions are temporarily disabled by admin.")
        return

    user_data = payments_collection.find_one({"user_id": user_id, "status": "approved"})
    if not user_data:
        await message.reply_text("You are not an approved subscriber. Use /clone after getting approved.")
        return

    ub_data = cloned_bots_collection.find_one({"user_id": user_id})
    if not ub_data:
        await message.reply_text("No UserBot session found. Use /clone <string> to start.")
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
        await message.reply_text("Your UserBot has been restarted. Type `.help` in your account to begin.")
    except Exception as e:
        logging.exception(f"Failed to restart UB via /startub: {e}")
        await message.reply_text("Something went wrong. Please check your session or contact support.")

# ------------------ Clone Client ------------------

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
                f"Username: @{bot_user.username or 'N/A'}\n"
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
        f"Username: @{user.username or 'N/A'}\n"
        f"DC ID: {user.dc_id}\n"
        f"Duration: {duration_data['days']} days"
    )

    for admin_id in HELPERS:
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
        
        await client.send_message(pyrecordcn, f"#NewPaymentCR\n\n"
                                              f"Name: {query.from_user.first_name}\n"
                                              f"User ID: {user_id}\n"
                                              f"Duration: {user_data['days']} days\n"
                                              f"Plan: ₹{user_data['amount']}")
        
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

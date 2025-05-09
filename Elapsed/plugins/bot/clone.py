import re
from datetime import datetime
import logging, asyncio
from pymongo import MongoClient
from pyrogram import Client, filters
from Elapsed import app as bot
from pyrogram.types import Message, ChatPrivileges 
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from config import API_ID, API_HASH, MONGO_DB_URI, OWNER_ID
from Elapsed.core.mongo import mongodb
from Elapsed.misc import SUDOERS
from Elapsed.utils.database import add_sudo, remove_sudo

mongo_client = MongoClient(MONGO_DB_URI)
mongo_db = mongo_client["Elapsed"]
mongo_collection = mongo_db["userbotdb"]

@bot.on_message(filters.command("clone") & filters.private)
async def on_clone(client, message):  
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        string_token = message.command[1]

        bots = list(mongo_collection.find())
        for bot in bots:
            if bot['string'] == string_token:
                await message.reply_text("➢ This Assistant UserBot is already cloned. Use /startub if it's off.")
                return

        ai = Client(
            f"{user_name}", API_ID, API_HASH,
            session_string=string_token,
            plugins={"root": "Elapsed.plugins.userbot"},
        )

        await ai.start()
        await ai.join_chat("phoenixXsupport")
        await ai.join_chat("TeamArona")
        await ai.join_chat("arona_update")
        await ai.join_chat("Grabber_memes")
        await ai.join_chat("Mystic_Legion")
        await ai.join_chat("PhoenixGban")
        await ai.join_chat("arona_gban")

        bot_user = await ai.get_me()
        details = {
            'is_bot': False,
            'user_id': user_id,
            'name': bot_user.first_name,
            'string': string_token,
            'username': bot_user.username
        }
        mongo_collection.insert_one(details)
        await message.reply_text(
            f"<b>Successfully cloned your Assistant UserBot: @{bot_user.username}.\n\nUse .start to activate. For help, type .help</b>"
        )

    except Exception as e:
        logging.exception(f"Error while cloning ub: {e}")
        await message.reply_text(f"⚠️ <b>Assistant UserBot Error:</b>\n\n<code>{e}</code>\n\n**Forward this message to the owner for assistance.**")

@bot.on_message(filters.command("deleteclone") & filters.private)
async def delete_cloned_bot(client, message):
    try:
        if message.reply_to_message:
            string_token = message.reply_to_message.text
        elif len(message.command) != 1:
            string_token = message.text.split(None, 1)[1]
        else:
            await message.reply_text("➢ Use this command with your session. Example: /deleteclone <your session>")
            return

        cloned_bot = mongo_collection.find_one({"string": string_token})
        if cloned_bot:
            mongo_collection.delete_one({"string": string_token})
            await message.reply_text("➢ Assistant UserBot has been removed and deleted from the database.")
    except Exception as e:
        logging.exception(f"Error while deleting Assistant UserBot: {e}")
        await message.reply_text("An error occurred while deleting the Assistant UserBot.")

@bot.on_message(filters.command("startallub", ".") & filters.user(OWNER_ID))
async def startall_botsss(_, m):
    bots = list(mongo_collection.find())
    for bot in bots:
        try:
            ai = Client(
                f"{bot['string']}", API_ID, API_HASH,
                session_string=bot['string'],
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.start()
            await ai.join_chat("phoenixXsupport")
            await ai.join_chat("TeamArona")
            await ai.join_chat("arona_update")
            await ai.join_chat("grabber_memes")
            await ai.join_chat("Mystic_Legion")
            await ai.join_chat("PhoenixGban")
            await ai.join_chat("arona_gban")
        except Exception as e:
            logging.exception(f"Error while restarting assistant {bot['string']}: {e}")

@bot.on_message(filters.command("stopallub", ".") & filters.user(OWNER_ID))
async def stop_All_ub(_, __):
    bots = list(mongo_collection.find())
    for bot in bots:
        try:
            ai = Client(
                f"{bot['string']}", API_ID, API_HASH,
                session_string=bot['string'],
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.stop()
        except Exception as e:
            logging.exception(f"Error while stopping assistant {bot['string']}: {e}")

@bot.on_message(filters.command("allclient", ".") & filters.user(OWNER_ID))
async def akll(_, m):
    bots = list(mongo_collection.find())
    all_client = "All Clients:\n"
    for bot in bots:
        all_client += f"{bot['user_id']} : {bot['name']}\n"
    await m.reply(all_client)

@bot.on_message(filters.command("startclient") & filters.private & filters.user(OWNER_ID))
async def start_client_owner(_, message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.text.split(None, 1)[1]
    cloned_bot = mongo_collection.find_one({"user_id": int(user_id)})

    if cloned_bot:
        string_token = cloned_bot.get("string")
        try:
            ai = Client(
                f"{string_token}", API_ID, API_HASH,
                session_string=string_token,
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.start()
            await ai.join_chat("phoenixXsupport")
            await ai.join_chat("TeamArona")
            await ai.join_chat("arona_update")
            await ai.join_chat("Grabber_memes")
            await ai.join_chat("Mystic_Legion")
            await ai.join_chat("PhoenixGban")
            await ai.join_chat("arona_gban")
            await message.reply("Client started. Use .ping")
        except Exception as e:
            logging.exception(f"Error while restarting assistant {string_token}: {e}")
    else:
        await message.reply("No cloned assistant found for your user ID.")

@bot.on_message(filters.command("stopclient") & filters.private & filters.user(OWNER_ID))
async def stop_ub_client(_, message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.text.split(None, 1)[1]
    cloned_bot = mongo_collection.find_one({"user_id": int(user_id)})

    if cloned_bot:
        string_token = cloned_bot.get("string")
        try:
            ai = Client(
                f"{string_token}", API_ID, API_HASH,
                session_string=string_token,
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.stop()
        except Exception as e:
            logging.exception(f"Error while stopping assistant {string_token}: {e}")
    else:
        await message.reply("No cloned assistant found for your user ID.")

@bot.on_message(filters.command("stopub") & filters.private)
async def stop_ub(_, message):
    cloned_bot = mongo_collection.find_one({"user_id": message.from_user.id})

    if cloned_bot:
        string_token = cloned_bot.get("string")
        try:
            ai = Client(
                f"{string_token}", API_ID, API_HASH,
                session_string=string_token,
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.stop()
            await message.reply("Client stopped.")
        except Exception as e:
            logging.exception(f"Error while stopping assistant {string_token}: {e}")
    else:
        await message.reply("No cloned assistant found for your user ID.")

@bot.on_message(filters.command("startub") & filters.private)
async def restartub(_, message):
    cloned_bot = mongo_collection.find_one({"user_id": message.from_user.id})

    if cloned_bot:
        string_token = cloned_bot.get("string")
        try:
            ai = Client(
                f"{string_token}", API_ID, API_HASH,
                session_string=string_token,
                plugins={"root": "Elapsed.plugins.userbot"},
            )
            await ai.start()
            await ai.join_chat("phoenixXsupport")
            await ai.join_chat("TeamArona")
            await ai.join_chat("arona_update")
            await ai.join_chat("Grabber_memes")
            await ai.join_chat("Mystic_Legion")
            await ai.join_chat("PhoenixGban")
            await ai.join_chat("arona_gban")
            await message.reply("Client started. Use .ping")
        except Exception as e:
            logging.exception(f"Error while restarting assistant {string_token}: {e}")
    else:
        await message.reply("No cloned assistant found for your user ID.")

import asyncio
import importlib

from pyrogram import idle

import config
from Elapsed import LOGGER, app
from Elapsed.misc import sudo
from Elapsed.plugins import ALL_MODULES
from Elapsed.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS
from Elapsed.plugins.bot.clone import restart_bots


async def init():
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    await restart_bots()
    await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module("Elapsed.plugins" + all_module)
    LOGGER("Elapsed.plugins").info("Successfully Imported Modules...")
    LOGGER("Elapsed").info(
                        "\x20\x4d\x75\x73\x69\x63\x20\x53\x74\x61\x72\x74\x65\x64\x20\x53\x75\x63\x63\x65\x73\x73\x66\x75\x6c\x6c\x79\x2e\x0a\x0a\x44\x6f\x6e\x27\x74\x20\x66\x6f\x72\x67\x65\x74\x20\x74\x6f\x20\x76\x69\x73\x69\x74\x20"
    )
    await idle()
    await app.stop()
    await userbot.stop()
    LOGGER("Elapsed").info("Stopping Elapsed Bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
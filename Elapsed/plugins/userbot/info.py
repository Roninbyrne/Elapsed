from pyrogram import filters, Client
from pyrogram.enums import ParseMode, UserStatus
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

def get_user_status(status):
    """Converts UserStatus enum to a readable string."""
    if status == UserStatus.ONLINE:
        return "online"
    elif status == UserStatus.OFFLINE:
        return "User is offline"
    elif status == UserStatus.RECENTLY:
        return "last seen recently"
    elif status == UserStatus.LAST_WEEK:
        return "last seen within a week"
    elif status == UserStatus.LAST_MONTH:
        return "last seen within a month"
    else:
        return "last seen a long time ago"

@Client.on_message(filters.command(["info"], prefixes=["."]) & (filters.group | filters.channel | filters.private) & filters.me)
async def info_user(_, message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user.id
    elif len(message.command) == 1:
        user = message.from_user.id
    else:
        user = message.text.split(None, 1)[1]

    m = await message.edit_text("ɢᴇᴛᴛɪɴɢ ᴜsᴇʀɪɴғᴏ")

    try:
        hm = await _.get_users(user_ids=user)
        if isinstance(hm, list):
            hm = hm[0]
    except Exception as e:
        return await m.edit_text(f"Error: {str(e)}", parse_mode=ParseMode.HTML)

    userinfo = f"""<b><u>ᴜsᴇʀ ɪɴғᴏ</u>
    ᴜsᴇʀ ɪᴅ: <code>{hm.id}</code>
    ғɪʀsᴛ ɴᴀᴍᴇ: {hm.first_name}
    ʟᴀsᴛ ɴᴀᴍᴇ: {hm.last_name if hm.last_name else ""}
    ᴜsᴇʀɴᴀᴍᴇ: {"@" + hm.username if hm.username else ""}
    ʟɪɴᴋ: {hm.mention}
    sᴛᴀᴛᴜs: {get_user_status(hm.status)}
    ᴅᴄ ɪᴅ: <code>{hm.dc_id}</code>
    ᴘʀᴇᴍɪᴜᴍ: <code>{hm.is_premium}</code>
    ʟᴀɴɢᴜᴀɢᴇ ᴄᴏᴅᴇ: <code>{hm.language_code}</code></b>
    """

    await m.edit_text(userinfo, parse_mode=ParseMode.HTML)

    await asyncio.sleep(20)
    await m.delete()

@Client.on_message(filters.command(["ginfo"], prefixes=["."]) & (filters.group | filters.channel | filters.private) & filters.me)
async def giinfo_user(_, message):
    if message.reply_to_message:
        chat_id = message.reply_to_message.chat.id
    elif len(message.command) == 1:
        chat_id = message.chat.id
    else:
        chat_id = message.text.split(None, 1)[1]

    chat_id = chat_id.lstrip('@')

    try:
        chat_id = int(chat_id)
    except ValueError:
        pass

    m = await message.edit_text("ɢᴇᴛᴛɪɴɢ ɪɴғᴏ")

    try:
        chat_info = await _.get_chat(chat_id=chat_id)
        total_members = await _.get_chat_members_count(chat_id)
        bots = 0

        async for member in _.get_chat_members(chat_id):
            if member.user.is_bot:
                bots += 1

    except Exception as e:
        return await m.edit_text(f"Error: {str(e)}", parse_mode=ParseMode.HTML)

    chatinfo = f"""<b><u>ᴄʜᴀᴛ ɪɴғᴏ</u>
    ᴄʜᴀᴛ ɪᴅ: <code>{chat_info.id}</code>
    Tɪᴛʟᴇ: {chat_info.title}
    ᴜsᴇʀɴᴀᴍᴇ: {"@" + chat_info.username if chat_info.username else ""}
    ᴅᴄ ɪᴅ: <code>{chat_info.dc_id}</code>
    ᴛᴏᴛᴀʟ ᴍᴇᴍʙᴇʀs: <code>{total_members}</code>
    ᴛᴏᴛᴀʟ ʙᴏᴛs: <code>{bots}</code></b>
    """

    await m.edit_text(chatinfo, parse_mode=ParseMode.HTML)

    await asyncio.sleep(20)
    await m.delete()
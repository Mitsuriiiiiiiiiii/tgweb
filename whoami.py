import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID, API_HASH = 2040, 'b18441a1ff607e10a989891a5462e627'
s = open('session.txt').read().strip()


async def main():
    async with TelegramClient(StringSession(s), API_ID, API_HASH) as c:
        me = await c.get_me()
        print(me.id, me.first_name, me.last_name, me.username, me.phone)


asyncio.run(main())

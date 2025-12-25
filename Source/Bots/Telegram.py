import os
import asyncio
from typing import Any, Dict
import logging

from discord import File, Embed
from telethon import events, TelegramClient
from telethon.errors.rpcerrorlist import UsernameInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPeerChannel, InputChannel

from .. import webhooks, config
from ..Formatting import format_single_article

logger = logging.getLogger("telegram")

image_download_path = os.path.join(
    os.getcwd(),
    str(config["Telegram"].get("ImageDownloadFolder", "TelegramImages")),
)

telegram_feed_list_urls = {
    'ArvinGroup': 'https://t.me/arvin_club',
    'VxUnderground': 'https://t.me/vxunderground',
    'Malpedia': 'https://t.me/malpedia',
    'LogsFree': 'https://t.me/locativelogsfree',
    'Darknet': 'https://t.me/dbforall',
    'GonjeshkeDarand': 'https://t.me/GonjeshkeDarand',
    'PryntStealer': 'https://t.me/officialpryntsoftware',
    'SiegedSec': 'https://t.me/SiegedSec',
    'BreachedForums': 'https://t.me/breached_co',
    'ArmyofThieves': 'https://t.me/ArmyThieves',
    'SharpBoys': 'https://t.me/sharpboys_3',
    'WLxDCONFIGS': 'https://t.me/WLxD_CRX',
    'TommyFlounder': 'https://t.me/floundertech',
    'GhostSec': 'https://t.me/GhostSecc',
    'ConfigMaster': 'https://t.me/config_combos',
    'Zer0DayLab': 'https://t.me/zer0daylab',
    'HADESSHOP': 'https://t.me/hadesh0p',
    'NoHideSpace': 'https://t.me/nohidespace',
    'KILLNET': 'https://t.me/killnet_reservs',
    'LOLZTEAM': 'https://t.me/lolz_guru',
    'Ares': 'https://t.me/aresmainchannel',
    'ZeroDayToday': 'https://t.me/LearnExploit',
    'CPartisan': 'https://t.me/cpartisans',
    'club1337': 'https://t.me/club1337',
    'Documentor': 'https://t.me/documentors',
    'DDoSecrets': 'https://t.me/AntiPlumbers',
    'SnatchTeam': 'https://t.me/snatch_news',
    'inj3ct0r': 'https://t.me/inj3ct0rs',
    'RalfHacker': 'https://t.me/RalfHackerChannel',
    'RuHeight': 'https://t.me/ruheight',
    'Data1eaks': 'https://t.me/data1eaks',
    'R0Crew': 'https://t.me/R0_Crew',
    'HeawsNet': 'https://t.me/heawsnet'
}

telegram_feed_list: Dict[str, Dict[str, Any]] = {}
for name, url in telegram_feed_list_urls.items():
    telegram_feed_list[name] = {"url" : url, "channel" : None}


def send_file_sync(path: str) -> None:
    with open(path, "rb") as upload_file:
        webhooks["TelegramFeed"].send(file=File(upload_file))

def send_embed_sync(embed: Embed) -> None:
    webhooks["TelegramFeed"].send(embed=embed)

async def event_handler(event: Any) -> None:
    if event.photo:
        logger.debug("Downloading image...")

        image_data = await event.download_media(os.path.join(image_download_path, str(event.photo.id)))
        await asyncio.get_running_loop().run_in_executor(None, send_file_sync, image_data)

    await create_telegram_output(event.chat, event.message)


async def create_telegram_output(chat: Any, message: Any) -> None:
    embed = format_single_article({"title" : message.message, "source" : f"{chat.title} | Telegram", "publish_date" : message.date})
    await asyncio.get_running_loop().run_in_executor(None, send_embed_sync, embed)


# Instatiate object per feed item
async def init_client(client: TelegramClient) -> None:
    for feed in telegram_feed_list.keys():
        try:  # TODO consider only sending join requests if not already joined
            url = telegram_feed_list[feed]["url"]
            logger.debug(f'Joining "{feed}" channel at {url}')
            
            # Get input entity for joining
            input_entity = await client.get_input_entity(url)
            if isinstance(input_entity, InputPeerChannel):
                input_channel = InputChannel(input_entity.channel_id, input_entity.access_hash)
                await client(JoinChannelRequest(input_channel))
            
            # Store channel entity if needed (though not currently used)
            telegram_feed_list[feed]["channel"] = await client.get_entity(url)
            
        except (
            UsernameInvalidError,
            ValueError
        ) as e:  # telegram user or channel was not found
            logger.warning(f'Problem when attempting to join "{feed}" channel at {telegram_feed_list[feed]["url"]}', exc_info=e)
            continue

    logger.debug("Registering event handler for handling new messages")
    client.add_event_handler(event_handler, events.NewMessage(incoming=True))


async def main_async() -> None:
    async with TelegramClient(
        config["Telegram"]["BotName"],
        int(config["Telegram"]["APIID"]),
        config["Telegram"]["APIHash"],
    ) as client:
        logger.info("Initiating telegram client")
        await init_client(client)
        await client.run_until_disconnected()

def main() -> None:
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

from loguru import logger

from .database import connection_pool
from .bot import bot
from .views import CampaignView
from . import constants


def setup():
    @bot.event
    async def on_ready():
        await connection_pool.open()
        bot.add_view(CampaignView())
        logger.info(
            f"We have logged in as {bot.user}. "
            "Add to your server: "
            "https://discord.com/oauth2/authorize?"
            f"client_id={bot.user.id}"
            f"&scope={constants.REQUIRED_SCOPES}"
            f"&permissions={constants.REQUIRED_PERMISSIONS}"
            "\n--------------------------------------------------\n"
        )

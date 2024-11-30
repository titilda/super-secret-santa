from .config import config
from .bot import bot

if __name__ == "__main__":
    bot.run(config.get("Discord", "token"))

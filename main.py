import g4f
from utils.Bot import DiscordBot
import os
from dotenv import load_dotenv

"""
Discord Developer Portal: https://discord.com/developers/applications
"""

if __name__ == "__main__":
    print("g4f Package Version: ", g4f.version)

    # Load environment variables from .env
    load_dotenv()

    # Access the environment variables (REQUIRED)
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    OWNER_USER_ID = int(os.getenv("OWNER_USER_ID"))
    # (Optional)
    BOT_JOIN_URL = os.getenv("BOT_JOIN_URL")

    # Instantiates and Runs Discord Bot
    Discord_Bot = DiscordBot(BOT_TOKEN, OWNER_USER_ID)
    Discord_Bot.run()

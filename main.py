import os
from time import sleep
from dotenv import load_dotenv
import asyncio
from skay.Logger import setup_logger
from skay.Bot import Bot

load_dotenv()

logger = setup_logger(os.getenv("BOT_NAME"))

bot = Bot()


def run():
    try:
        bot.setSession()
        bot.start()
    except KeyboardInterrupt:
        logger.info('Keyboard interrupt received, shutting down...')
    # except Exception as e:
    #     logger.error(e)
    #     sleep(60)
    #     run()


if __name__ == "__main__":
    run()

import argparse
import asyncio
import distutils.util
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from os import getenv
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import discord
import seaborn as sns
from discord.ext import commands
from matplotlib import pyplot as plt

from tle import constants
from tle.util import codeforces_common as cf_common
from tle.util import discord_common, font_downloader


async def setup():
    # Make required directories.
    for path in constants.ALL_DIRS:
        os.makedirs(path, exist_ok=True)

    # logging to console and file on daily interval
    logging.basicConfig(format='{asctime}:{levelname}:{name}:{message}', style='{',
                        datefmt='%d-%m-%Y %H:%M:%S', level=logging.INFO,
                        handlers=[logging.StreamHandler(),
                                  TimedRotatingFileHandler(constants.LOG_FILE_PATH, when='D',
                                                           backupCount=3, utc=True)])

    # matplotlib and seaborn
    plt.rcParams['figure.figsize'] = 7.0, 3.5
    sns.set()
    options = {
        'axes.edgecolor': '#A0A0C5',
        'axes.spines.top': False,
        'axes.spines.right': False,
    }
    sns.set_style('darkgrid', options)

    # Download fonts if necessary
    await font_downloader.maybe_download()


class Bot(commands.Bot):

    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or(';'), intents=intents)

    async def setup_hook(self) -> None:
        await setup()
        cogs = [file.stem for file in Path('tle', 'cogs').glob('*.py')]
        for extension in cogs:
            await self.load_extension(f'tle.cogs.{extension}')
        logging.info(f'Cogs loaded: {", ".join(self.cogs)}')
        

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodb', action='store_true')
    args = parser.parse_args()

    token = getenv('BOT_TOKEN')
    if not token:
        logging.error('Token required')
        return

    allow_self_register = getenv('ALLOW_DUEL_SELF_REGISTER')
    if allow_self_register:
        # constants.ALLOW_DUEL_SELF_REGISTER = bool(distutils.util.strtobool(allow_self_register))
        constants.ALLOW_DUEL_SELF_REGISTER = allow_self_register in ["true", "True", "TRUE"]

    bot = Bot()

    def no_dm_check(ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage('Private messages not permitted.')
        return True

    # Restrict bot usage to inside guild channels only.
    bot.add_check(no_dm_check)

    # cf_common.initialize needs to run first, so it must be set as the bot's
    # on_ready event handler rather than an on_ready listener.
    @discord_common.on_ready_event_once(bot)
    async def init():
        await cf_common.initialize(args.nodb)
        asyncio.create_task(discord_common.presence(bot))

    bot.add_listener(discord_common.bot_error_handler, name='on_command_error')
    bot.run(token)


if __name__ == '__main__':
    main()

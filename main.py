import argparse
import logging

import bot
import config

# init argparse
parser = argparse.ArgumentParser(description='run splatoon3 bot')
parser.add_argument('-c', '--config', type=str, required=True, metavar='<config_path>', help='path to config')
parser.add_argument('-t', '--token', type=str, required=True, metavar='<telegram_bot_token>', help='bot\'s API token')
parser.add_argument('-w', '--whitelist', type=str, action='append', metavar='<username>', help='whitelisted users that bot will response to')
parser.add_argument('--overwrite', type=str, action='append', metavar='<config_key>=<value>', help='overwrite config')
args = parser.parse_args()

# init config
config.load(args.config, args_overwrite=args.overwrite)
config.set(config.BOT_TOKEN, args.token)
config.set(config.BOT_WHITELIST, args.whitelist)

# init logging
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] - %(message)s',
    level=logging.getLevelName(config.get(config.LOGGING_LEVEL).upper())
)

# run bot
bot.run()

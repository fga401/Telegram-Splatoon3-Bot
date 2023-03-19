import argparse
import logging

import config

# init argparse
parser = argparse.ArgumentParser(description='run splatoon3 bot')
parser.add_argument('-c', '--config', type=str, required=True, metavar='<config_path>', help='path to config.')
parser.add_argument('-t', '--token', type=str, required=True, metavar='<telegram_bot_token>', help='bot\'s API token.')
parser.add_argument('-u', '--user', type=str, action='append', default=[], metavar='<username>', help='whitelisted users that bot will response to.')
parser.add_argument('-U', '--admin', type=str, action='append', default=[], metavar='<username>', help='admin users. They will be treated as whitelisted users too.')
parser.add_argument('--overwrite', type=str, action='append', metavar='<config_key>=<value>', help='overwrite config.')
parser.add_argument('-s', '--storage-channel', type=str, required=True, metavar='<channel_id>', help='a channel that saves images.')
args = parser.parse_args()

# init config
config.load(args.config, args_overwrite=args.overwrite)
config.set(config.BOT_TOKEN, args.token)
config.set(config.BOT_ADMIN, set(args.admin))
config.set(config.BOT_WHITELIST, set(args.user + args.admin))

# init logging
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
    level=logging.getLevelName(config.get(config.LOGGING_LEVEL).upper())
)

if __name__ == '__main__':
    import bot

    # run bot
    bot.run()

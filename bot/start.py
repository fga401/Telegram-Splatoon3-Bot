from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bot import profiles
from bot.data import BotData
from bot.utils import whitelist_filter


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profiles.init_user_data(context)
    context.bot_data[BotData.RegisteredUsers].add(update.message.from_user.id)
    await profiles.profile_manage(update, context)

handlers = [
    CommandHandler('start', start, filters=whitelist_filter),
]
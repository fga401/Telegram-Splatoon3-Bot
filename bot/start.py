from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bot import profiles
from bot.whitelist import whitelist_filter


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profiles.init_user_data(context)
    await profiles.profile_manage(update, context)

handlers = [
    CommandHandler('start', start, filters=whitelist_filter),
]
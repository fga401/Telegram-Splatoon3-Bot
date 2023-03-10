from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from locales import _


class SettingsButtonCallback:
    regexp = 'SETTINGS_.+'
    Add = 'SETTINGS_ADD'
    Edit = 'SETTINGS_EDIT'
    Delete = 'SETTINGS_DELETE'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(_('Add Account'), callback_data=SettingsButtonCallback.Add),
            InlineKeyboardButton(_('Edit Account'), callback_data=SettingsButtonCallback.Edit),
            InlineKeyboardButton(_('Delete Account'), callback_data=SettingsButtonCallback.Delete),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(_('Please choose:'), reply_markup=reply_markup)


async def settings_button_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=f'Selected option: {"ADD"}')

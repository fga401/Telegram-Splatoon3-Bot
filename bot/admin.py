import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

from bot.nintendo import stage_schedule
from bot.schedules import update_schedule_image
from bot.utils import admin_filter, current_profile
from locales import _

logger = logging.getLogger('bot.admin')


class AdminButtonCallback:
    Schedules = 'ADMIN_SCHEDULES'
    Exit = 'ADMIN_EXIT'


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(_('Force Update Schedules'), callback_data=AdminButtonCallback.Schedules),
        ],
        [
            InlineKeyboardButton(_('« Go Back'), callback_data=AdminButtonCallback.Exit),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=_('Admin Options:'), reply_markup=reply_markup)


async def admin_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text=_('Exited admin settings.'))


async def admin_update_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(text=_('Updating schedules...'))
    profile = current_profile(context)
    resp = await stage_schedule(profile)
    logger.info(f'Got schedules. schedules={resp}')
    await update_schedule_image(resp, profile, context, force=True)
    await query.edit_message_text(text=_('Schedules have been updated.'))


def init_admin(application: Application):
    application.add_handlers(handlers)


handlers = [
    CommandHandler('admin', admin_menu, filters=admin_filter),
    CallbackQueryHandler(admin_update_schedules, pattern=AdminButtonCallback.Schedules),
    CallbackQueryHandler(admin_exit, pattern=AdminButtonCallback.Exit),
]

import datetime
from copy import copy
from typing import Callable, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, Application
from telegram.ext.filters import MessageFilter

import config
import locales
import nintendo.login
import nintendo.utils
from bot.data import UserData, Profile
from bot.utils import CallbackData, whitelist_filter
from locales import _


class ProfileButtonCallback:
    List = 'PROFILE_LIST'
    Manage = 'PROFILE_MANAGE'
    Add = 'PROFILE_ADD'
    Exit = 'PROFILE_EXIT'
    Cancel = 'PROFILE_CANCEL_INPUT'
    Use = CallbackData('PROFILE_USE')
    Detail = CallbackData('PROFILE_DETAIL')
    Delete = CallbackData('PROFILE_DELETE')
    Language = CallbackData('PROFILE_LANG')


class ProfileAddingState:
    Link = 0
    Timezone = 1
    Language = 2
    Name = 3


def init_user_data(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.setdefault(UserData.Current, -1)
    context.user_data.setdefault(UserData.Profiles, dict())
    context.user_data.setdefault(UserData.Pending, Profile())
    context.user_data.setdefault(UserData.Verifier, '')
    context.user_data.setdefault(UserData.MessageID_Name, '')
    context.user_data.setdefault(UserData.MessageID_Link, '')
    context.user_data.setdefault(UserData.MessageID_Timezone, '')


async def profile_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is not None:
        await query.answer()

    current_profile = context.user_data[UserData.Current]
    profiles: dict[int, Profile] = context.user_data[UserData.Profiles]
    if len(profiles) < 2:
        await profile_manage(update, context)
        return
    profile_keyboard = [
        [InlineKeyboardButton(__show_profile_name(p.name, p.id == current_profile), callback_data=ProfileButtonCallback.Use.encode(str(p.id)))] for p in sorted(profiles.values(), key=lambda x: x.id)
    ]
    other_keyboard = [
        [
            InlineKeyboardButton(_('« Go Back'), callback_data=ProfileButtonCallback.Exit),
            InlineKeyboardButton(_('Manage Profile »'), callback_data=ProfileButtonCallback.Manage)
        ],
    ]
    reply_markup = InlineKeyboardMarkup(profile_keyboard + other_keyboard)

    async def __reply():
        if query is not None:
            await query.edit_message_text(text=_('Here are your profiles ({}/{}). ').format(len(profiles), config.get(config.APP_MAX_PROFILE)) + _('Choose your new profile.'), reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=_('Here are your profiles ({}/{}). ').format(len(profiles), config.get(config.APP_MAX_PROFILE)) + _('Choose your new profile.'), reply_markup=reply_markup)

    await __reply()


async def profile_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(_('Exited profile settings.'))


async def profile_manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is not None:
        await query.answer()
    current_profile = context.user_data[UserData.Current]
    profiles: dict[int, Profile] = context.user_data[UserData.Profiles]
    profile_keyboard = [
        [InlineKeyboardButton(__show_profile_name(p.name, p.id == current_profile), callback_data=ProfileButtonCallback.Detail.encode(str(p.id)))] for p in sorted(profiles.values(), key=lambda x: x.id)
    ]
    other_keyboard = [[]]
    if len(profiles) == 0:
        text = _('You don\'t have any profile. Would you like to add one?')
    else:
        text = _('Here are your profiles ({}/{}). ').format(len(profiles), config.get(config.APP_MAX_PROFILE)) + _('Choose a profile to delete, or add a new profile.')
    if len(profiles) >= 2:
        other_keyboard[0].append(InlineKeyboardButton(_('« Go Back'), callback_data=ProfileButtonCallback.List))
    else:
        other_keyboard[0].append(InlineKeyboardButton(_('« Go Back'), callback_data=ProfileButtonCallback.Exit))
    if len(profiles) < config.get(config.APP_MAX_PROFILE):
        other_keyboard[0].append(InlineKeyboardButton(_('Add Profile »'), callback_data=ProfileButtonCallback.Add))
    reply_markup = InlineKeyboardMarkup(profile_keyboard + other_keyboard)

    async def __reply():
        if query is not None:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)

    await __reply()
    return ConversationHandler.END


async def profile_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    profile_id: int = int(ProfileButtonCallback.Detail.decode(query.data))
    profile: Profile = context.user_data[UserData.Profiles][profile_id]
    keyboard = [
        [
            InlineKeyboardButton(_('« No'), callback_data=ProfileButtonCallback.Manage),
            InlineKeyboardButton(_('Yes »'), callback_data=ProfileButtonCallback.Delete.encode(str(profile_id))),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=_('Are you sure to delete this profile?') + __message_profile_detail(_, profile), reply_markup=reply_markup)


async def profile_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is not None:
        await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(text=_('« Go Back'), callback_data=ProfileButtonCallback.Manage),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    profiles: dict[int, Profile] = context.user_data[UserData.Profiles]
    if len(profiles) >= config.get(config.APP_MAX_PROFILE):
        if query is not None:
            await query.edit_message_text(text=_('The number of profiles has reached the limit.'), reply_markup=reply_markup)
        else:
            await update.message.reply_text(text=_('The number of profiles has reached the limit.'), reply_markup=reply_markup)
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton(text=_('« Cancel'), callback_data=ProfileButtonCallback.Cancel),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query is not None:
        message = await query.edit_message_text(text=_('Please send the <b>[Profile Name]</b>.\n') + __message_profile_name_pattern(_), reply_markup=reply_markup)
    else:
        message = await update.message.reply_text(text=_('Please send the <b>[Profile Name]</b>.\n') + __message_profile_name_pattern(_), reply_markup=reply_markup)
    context.user_data[UserData.MessageID_Name] = message.id
    return ProfileAddingState.Name


async def profile_input_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    profile_name = update.message.text
    profiles: dict[int, Profile] = context.user_data[UserData.Profiles]
    if profile_name in profiles:
        await update.message.reply_text(text=_('Profile <b>[{}]</b> already existed. Please choose a new name.\n').format(profile_name) + __message_profile_name_pattern(_))
        return ProfileAddingState.Name
    context.user_data[UserData.Pending].name = profile_name

    context.user_data[UserData.Verifier], link = nintendo.login.login_link()
    await context.application.bot.edit_message_text(chat_id=update.message.chat_id, message_id=context.user_data[UserData.MessageID_Name], text=_('You input the <b>[Profile Name]</b>: <b>[{}]</b>.').format(profile_name))
    keyboard = [
        [
            InlineKeyboardButton(text=_('Login'), url=link),
        ],
        [
            InlineKeyboardButton(text=_('« Cancel'), callback_data=ProfileButtonCallback.Cancel),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text(text=_('Please open the page, copy the <b>[link]</b> of <b>[Select this account]</b> and send it here.\n'), reply_markup=reply_markup)
    context.user_data[UserData.MessageID_Link] = message.id
    return ProfileAddingState.Link


async def profile_input_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = await update.message.reply_text(text=_('Processing your link...'))

    link = update.message.text
    auth_code_verifier = context.user_data[UserData.Verifier]

    try:
        session_token = await nintendo.login.get_session_token(auth_code_verifier, link)
        web_service_token, user_nickname, user_lang, user_country = await nintendo.login.get_gtoken(session_token)
        bullet_token = await nintendo.login.get_bullet(web_service_token, user_lang, user_country)
    except nintendo.utils.NintendoError as e:
        await update.message.reply_text(text=_('Failed to get your Nintendo token. Please retry.\nerror = {}').format(e))
        return ProfileAddingState.Link
    pending_profile: Profile = context.user_data[UserData.Pending]
    pending_profile.account_name = user_nickname
    pending_profile.session_token = session_token
    pending_profile.gtoken = web_service_token
    pending_profile.bullet_token = bullet_token
    pending_profile.country = user_country

    await context.application.bot.delete_message(chat_id=message.chat_id, message_id=message.id)
    await context.application.bot.edit_message_text(chat_id=update.message.chat_id, message_id=context.user_data[UserData.MessageID_Link], text=_('Your account is <b>[{}]</b>.').format(user_nickname))
    keyboard = [
        [InlineKeyboardButton(l, callback_data=ProfileButtonCallback.Language.encode(l))] for l in locales.available_languages
    ]
    cancel_keyboard = [
        [
            InlineKeyboardButton(text=_('« Cancel'), callback_data=ProfileButtonCallback.Cancel),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard + cancel_keyboard)
    await update.message.reply_text(text=_('Please choose your preferred <b>[Language]</b>.\n'), reply_markup=reply_markup)
    return ProfileAddingState.Language


async def profile_input_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    language = ProfileButtonCallback.Language.decode(query.data)
    context.user_data[UserData.Pending].language = language

    await query.edit_message_text(text=_('You chose preferred <b>[Language]</b>: <b>[{}]</b>').format(language))
    keyboard = [
        [
            InlineKeyboardButton(text=_('« Cancel'), callback_data=ProfileButtonCallback.Cancel),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await query.message.reply_text(text=_('Please send the <b>[Timezone]</b>.\n') + __message_profile_timezone_pattern(_), reply_markup=reply_markup)
    context.user_data[UserData.MessageID_Timezone] = message.id
    return ProfileAddingState.Timezone


async def profile_input_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    timezone = update.message.text
    context.user_data[UserData.Pending].timezone = timezone

    result = __create_profile(context)
    await context.application.bot.edit_message_text(chat_id=update.message.chat_id, message_id=context.user_data[UserData.MessageID_Timezone], text=_('You input the <b>[Timezone]</b>: <b>[{}]</b>.').format(timezone))
    if len(context.user_data[UserData.Profiles]) > 1:
        callback_data = ProfileButtonCallback.List
    else:
        callback_data = ProfileButtonCallback.Manage
    back_keyboard = [
        [
            InlineKeyboardButton(_('« Go Back'), callback_data=callback_data),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(back_keyboard)
    if isinstance(result, int):
        profile = context.user_data[UserData.Profiles][result]
        await update.message.reply_text(text=_('Profile <b>[{}]</b> was added.').format(profile.name) + __message_profile_detail(_, profile), reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=_('Failed to add profile.\n') + result, reply_markup=reply_markup)
    return ConversationHandler.END


def __create_profile(context: ContextTypes.DEFAULT_TYPE) -> Union[int, str]:
    """
    return new profile id if success, else return reason of failure.
    """
    profiles: dict[int, Profile] = context.user_data[UserData.Profiles]
    if len(profiles) >= config.get(config.APP_MAX_PROFILE):
        return _('The number of profiles has reached the limit.')

    profile_ids = [p.id for p in profiles.values()]
    next_id = max(profile_ids, default=0) + 1
    pending_profile: Profile = copy(context.user_data[UserData.Pending])
    pending_profile.id = next_id

    profiles[pending_profile.id] = pending_profile
    context.user_data[UserData.Profiles] = profiles
    if context.user_data[UserData.Current] == -1:
        context.user_data[UserData.Current] = pending_profile.id
    return pending_profile.id


async def profile_input_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(text=_('« Go Back'), callback_data=ProfileButtonCallback.Manage),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = update.message or update.callback_query.message
    await message.reply_text(text=_('No input for a while. Adding profile has been canceled.'), reply_markup=reply_markup)
    return ConversationHandler.END


async def profile_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    profile_id: int = int(ProfileButtonCallback.Use.decode(query.data))
    context.user_data[UserData.Current] = profile_id
    profile = context.user_data[UserData.Profiles][profile_id]
    keyboard = [
        [
            InlineKeyboardButton(text=_('« Go Back'), callback_data=ProfileButtonCallback.List),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=_('Current profile is <b>[{}]</b>.').format(profile.name) + __message_profile_detail(_, profile), reply_markup=reply_markup)


async def profile_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    deleted_profile_id: int = int(ProfileButtonCallback.Delete.decode(query.data))
    deleted_profile: Profile = context.user_data[UserData.Profiles][deleted_profile_id]
    del context.user_data[UserData.Profiles][deleted_profile_id]
    if context.user_data[UserData.Current] == deleted_profile_id:
        sorted_profiles = sorted(context.user_data[UserData.Profiles].keys())
        if len(sorted_profiles) > 0:
            context.user_data[UserData.Current] = sorted_profiles[0]
        else:
            context.user_data[UserData.Current] = -1
    back_keyboard = [
        [
            InlineKeyboardButton(_('« Go Back'), callback_data=ProfileButtonCallback.Manage),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(back_keyboard)
    if context.user_data[UserData.Current] == -1:
        await query.edit_message_text(text=_('Profile <b>[{}]</b> was deleted.').format(deleted_profile.name) + __message_profile_detail(_, deleted_profile), reply_markup=reply_markup)
    else:
        next_profile_id = context.user_data[UserData.Current]
        next_profile = context.user_data[UserData.Profiles][next_profile_id]
        await query.edit_message_text(text=_('Profile <b>[{}]</b> was deleted.').format(deleted_profile.name) + _('Current profile is <b>[{}]</b>.').format(next_profile) + __message_profile_detail(_, next_profile), reply_markup=reply_markup)


def __show_profile_name(name: str, is_current: bool):
    if is_current:
        return f'* {name}'
    else:
        return f'  {name}'


def __message_profile_detail(_: Callable[[str], str], profile: Profile):
    return _('\n  - Profile Name = <b>[{}]</b>\n  - Account Name = <b>[{}]</b>\n  - Country = <b>[{}]</b>\n  - Language = <b>[{}]</b>\n  - Timezone = <b>[{}]</b>').format(profile.name, profile.account_name, profile.country, profile.language, profile.timezone)


def __message_profile_name_pattern(_: Callable[[str], str]):
    return _('  - format: <code>.{1,20}</code>\n  - example: <code>工</code>, <code>MyProfile</code>')


def __message_profile_timezone_pattern(_: Callable[[str], str]):
    return _('  - format: <code>(+|-)\\d+(\\.\\d*)?</code>\n  - example: <code>+8</code>, <code>-5.5</code>')


class LoginLinkFilter(MessageFilter):
    def filter(self, message: Message):
        return nintendo.utils.is_valid_login_link(message.text)


def init_profile(application: Application):
    application.add_handlers(handlers)


handlers = [
    CommandHandler('profiles', profile_list, filters=whitelist_filter),
    CallbackQueryHandler(profile_exit, pattern=ProfileButtonCallback.Exit),
    CallbackQueryHandler(profile_list, pattern=ProfileButtonCallback.List),
    CallbackQueryHandler(profile_use, pattern=ProfileButtonCallback.Use.pattern),
    CallbackQueryHandler(profile_manage, pattern=ProfileButtonCallback.Manage),
    CallbackQueryHandler(profile_detail, pattern=ProfileButtonCallback.Detail.pattern),
    CallbackQueryHandler(profile_delete, pattern=ProfileButtonCallback.Delete.pattern),
    ConversationHandler(
        entry_points=[CallbackQueryHandler(profile_add, pattern=ProfileButtonCallback.Add)],
        states={
            ProfileAddingState.Name: [
                MessageHandler(filters=whitelist_filter & filters.Regex(r'^.{1,20}$'), callback=profile_input_name),
                CallbackQueryHandler(profile_manage, pattern=ProfileButtonCallback.Cancel),
            ],
            ProfileAddingState.Link: [
                MessageHandler(filters=whitelist_filter & LoginLinkFilter(), callback=profile_input_link),
                CallbackQueryHandler(profile_manage, pattern=ProfileButtonCallback.Cancel),
            ],
            ProfileAddingState.Language: [
                CallbackQueryHandler(profile_input_language, pattern=ProfileButtonCallback.Language.pattern),
                CallbackQueryHandler(profile_manage, pattern=ProfileButtonCallback.Cancel),
            ],
            ProfileAddingState.Timezone: [
                MessageHandler(filters=whitelist_filter & filters.Regex(r'^(\+|-)\d+(\.\d*)?$'), callback=profile_input_timezone),
                CallbackQueryHandler(profile_manage, pattern=ProfileButtonCallback.Cancel),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters=whitelist_filter, callback=profile_input_timeout),
                CallbackQueryHandler(profile_input_timeout, pattern=ProfileButtonCallback.Add),
                CallbackQueryHandler(profile_input_timeout, pattern=ProfileButtonCallback.Language.pattern),
            ],
        },
        fallbacks=[],
        allow_reentry=True,
        conversation_timeout=datetime.timedelta(minutes=10).seconds,
        name='add_profile',
        persistent=True,
    )
]

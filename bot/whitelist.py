from telegram import Message
from telegram.ext.filters import MessageFilter

import config


class WhitelistFilter(MessageFilter):
    def filter(self, message: Message):
        return message.from_user.username in config.get(config.BOT_WHITELIST)


whitelist_filter = WhitelistFilter()

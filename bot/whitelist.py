from typing import Iterable

from telegram import Message
from telegram.ext.filters import MessageFilter


class WhitelistFilter(MessageFilter):
    def __init__(self, usernames: Iterable[str] = None):
        super().__init__()
        if usernames is not None:
            self.__usernames = set(usernames)

    def filter(self, message: Message):
        if self.__usernames is None:
            return True
        return message.from_user.username in self.__usernames

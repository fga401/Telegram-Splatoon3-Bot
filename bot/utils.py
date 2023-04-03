import datetime
import re
import sys
from dataclasses import dataclass
from typing import Tuple, Optional

from telegram import Message
from telegram._utils.types import ODVInput
from telegram.ext import ContextTypes
from telegram.ext.filters import MessageFilter
from telegram.request import HTTPXRequest
from telegram.request._baserequest import BaseRequest
from telegram.request._requestdata import RequestData

import config
import utils
from bot.data import Profile, UserData


class WhitelistFilter(MessageFilter):
    def __init__(self, whitelist: list[str]):
        super().__init__()
        self.whitelist = set(whitelist)

    def filter(self, message: Message):
        return message.from_user.username in self.whitelist


whitelist_filter = WhitelistFilter(config.get(config.BOT_WHITELIST))
admin_filter = WhitelistFilter(config.get(config.BOT_ADMIN))


class BackoffRetryRequest(HTTPXRequest):
    def __init__(
            self,
            connection_pool_size: int = 1,
            proxy_url: str = None,
            read_timeout: Optional[float] = 5.0,
            write_timeout: Optional[float] = 5.0,
            connect_timeout: Optional[float] = 5.0,
            pool_timeout: Optional[float] = 1.0,
            http_version: str = "2",
    ):
        super().__init__(
            connection_pool_size=connection_pool_size,
            proxy_url=proxy_url,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
            connect_timeout=connect_timeout,
            pool_timeout=pool_timeout,
            http_version=http_version
        )

    @utils.retry_with_backoff(retries=sys.maxsize)
    async def do_request(
            self,
            url: str,
            method: str,
            request_data: RequestData = None,
            read_timeout: ODVInput[float] = BaseRequest.DEFAULT_NONE,
            write_timeout: ODVInput[float] = BaseRequest.DEFAULT_NONE,
            connect_timeout: ODVInput[float] = BaseRequest.DEFAULT_NONE,
            pool_timeout: ODVInput[float] = BaseRequest.DEFAULT_NONE,
    ) -> Tuple[int, bytes]:
        return await super().do_request(url, method, request_data, read_timeout, write_timeout, connect_timeout, pool_timeout)


@dataclass
class CallbackData:
    __namespace: str

    def __post_init__(self):
        self._regex = re.compile(f'{self.__namespace}_(?P<value>.+)')

    def encode(self, value: str):
        return f'{self.__namespace}_{value}'

    def decode(self, string: str) -> str:
        return self._regex.search(string).group('value')

    @property
    def pattern(self):
        return f'{self.__namespace}_.+'


def current_profile(context: ContextTypes.DEFAULT_TYPE, user_id: str = None) -> Profile:
    if context.user_data is None:
        user_data = context.application.user_data[user_id]
    else:
        user_data = context.user_data
    return user_data[UserData.Profiles][user_data[UserData.Current]]


def format_schedule_time(time: datetime.datetime) -> str:
    return time.strftime('%m-%d %H:%M')


def format_detail_time(time: datetime.datetime) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S')

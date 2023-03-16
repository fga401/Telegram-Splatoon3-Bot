import re
import sys
from dataclasses import dataclass
from typing import Tuple

from telegram import Message
from telegram._utils.types import ODVInput
from telegram.ext.filters import MessageFilter
from telegram.request import HTTPXRequest
from telegram.request._baserequest import BaseRequest
from telegram.request._requestdata import RequestData

import config
import utils


class WhitelistFilter(MessageFilter):
    def filter(self, message: Message):
        return message.from_user.username in config.get(config.BOT_WHITELIST)


whitelist_filter = WhitelistFilter()


class BackoffRetryRequest(HTTPXRequest):
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

import re
from dataclasses import dataclass


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

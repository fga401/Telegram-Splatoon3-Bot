import json
import typing
from typing import List

import jsonpath_ng

config = None
overwrite_map = {}


def load(path: str, args_overwrite: List[str] = None):
    global config
    with open(path, "r") as f:
        config = json.load(f)
    if args_overwrite is not None:
        for i in args_overwrite:
            __parse_overwrite(i)


def get(key: str):
    global overwrite_map
    if key in overwrite_map:
        return overwrite_map[key]
    exp = jsonpath_ng.parse(key)
    ret = [match.value for match in exp.find(config)]
    return ret[0] if len(ret) == 1 else ret


def set(key: str, value):
    overwrite_map[key] = value


def __parse_overwrite(line: str):
    global overwrite_map
    key, value = line.split('=')
    old = get(key)
    t = type(old)
    if isinstance(old, List):
        new = [typing.cast(t, i) for i in value.split(',')]
    else:
        new = typing.cast(t, value)
    overwrite_map[key] = new

import asyncio
import functools
import logging
import random

from telegram.error import RetryAfter


def retry_with_backoff(retries=5, backoff_in_seconds=1, max_second=10, skipped_exception=None):
    def rwb(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    if skipped_exception is not None and isinstance(e, skipped_exception):
                        raise
                    if x == retries:
                        raise

                    else:
                        sleep = (backoff_in_seconds * 2 ** x + random.uniform(0, 1))
                        sleep = min(max_second, sleep)
                    await asyncio.sleep(sleep)
                    x += 1

        return wrapper

    return rwb

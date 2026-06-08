from typing import Any
from sentry_sdk import capture_exception
from django.conf import settings
from django.utils import timezone
import datetime


class Cache:
    expire_time = 0
    default = 0

    def __init__(self):
        self.data = self.default
        self.last_update = timezone.now() - datetime.timedelta(seconds=self.expire_time)
        self.invalid = True

    def update(self):
        raise NotImplementedError()

    def _update_cache(self):
        try:
            self.save(self.update())
            self.last_update = timezone.now()
            self.invalid = False
        except (SystemExit, KeyboardInterrupt) as e:
            # `update()` may issue a network call that hangs (see PolicyEngineBearerTokenCache),
            # in which case the worker can be torn down mid-fetch and SystemExit is raised here.
            # That is a BaseException, so `except Exception` below would miss it. Surface it,
            # then re-raise so the shutdown proceeds.
            capture_exception(e, level="error")
            raise
        except Exception as e:
            if settings.DEBUG:
                print(e)
            capture_exception(e, level="warning")

    def save(self, data):
        self.data = data

    def should_update(self):
        if self.invalid is True:
            return True

        return timezone.now() > self.last_update + datetime.timedelta(seconds=self.expire_time)

    def fetch(self) -> Any:
        if self.should_update():
            self._update_cache()

        return self.data

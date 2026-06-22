from .models import Screen
from programs.models import Referrer
from .serializers import ScreenSerializer
from sentry_sdk import capture_exception, capture_message
from typing import Optional
import requests


class Hook:
    def __init__(self, hook: Referrer) -> None:
        self.hook = hook
        self.functions = [func.name for func in hook.webhook_functions.all()]

    def send(self, screen: Screen, results: dict, force: bool = True) -> Optional[Exception]:
        if screen.completed and not force:
            return
        if self.hook.webhook_url is None:
            return

        request_data = {"external_id": screen.external_id}
        if "send_screen" in self.functions:
            key, value = self.screen_data(screen)
            request_data[key] = value
        if "send_results" in self.functions:
            key, value = self.send_eligibility(results)
            request_data[key] = value

        try:
            res = requests.post(self.hook.webhook_url, json=request_data, timeout=(5, 30))
            if res.status_code != 200:
                capture_message(f"{res.text}", level="error")
                return Exception(f"{res.status_code}: {res.text}")
        except requests.exceptions.RequestException as e:
            capture_exception(e)
            return e

    def screen_data(self, screen: Screen):
        # ScreenSerializer.to_representation reads the current_benefits join table;
        # prefetch current_benefits__program so it doesn't issue a per-send query.
        # (The viewset/eligibility paths prefetch this on their own querysets; the
        # webhook loads the screen separately, so do it here.)
        screen = Screen.objects.prefetch_related("current_benefits__program").get(pk=screen.pk)
        screen_dict = ScreenSerializer(screen).data
        return "screen", screen_dict

    def send_eligibility(self, results: dict):
        return "eligibility", results


def get_web_hook(screen: Screen) -> Optional[Hook]:
    if screen.referrer_code is None:
        return None

    try:
        referrer = Referrer.objects.get(white_label=screen.white_label, referrer_code=screen.referrer_code)
    except Referrer.DoesNotExist:
        return None

    return Hook(referrer)

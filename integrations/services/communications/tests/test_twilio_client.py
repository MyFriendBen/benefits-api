import threading
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from integrations.services.communications import twilio_client as tc


@override_settings(TWILIO_SID="AC1", TWILIO_TOKEN="t1")
class TwilioClientTest(SimpleTestCase):
    def setUp(self) -> None:
        self._reset()
        self.addCleanup(self._reset)
        client_patch = patch.object(tc, "Client", side_effect=lambda *a, **kw: MagicMock())
        self.client_cls = client_patch.start()
        self.addCleanup(client_patch.stop)

    @staticmethod
    def _reset() -> None:
        if hasattr(tc._local, "cached"):
            del tc._local.cached

    def test_reused_within_a_thread(self) -> None:
        self.assertIs(tc.twilio_client(), tc.twilio_client())
        self.assertEqual(self.client_cls.call_count, 1)

    def test_rebuilt_when_credentials_change(self) -> None:
        first = tc.twilio_client()
        with override_settings(TWILIO_SID="AC2", TWILIO_TOKEN="t2"):
            self.assertIsNot(tc.twilio_client(), first)
        self.assertEqual(self.client_cls.call_args.args, ("AC2", "t2"))

    def test_each_thread_gets_its_own(self) -> None:
        mine = tc.twilio_client()
        theirs: list[object] = []
        thread = threading.Thread(target=lambda: theirs.append(tc.twilio_client()))
        thread.start()
        thread.join()
        self.assertIsNot(theirs[0], mine)

    def test_requests_have_a_timeout(self) -> None:
        tc.twilio_client()
        http_client = self.client_cls.call_args.kwargs["http_client"]
        self.assertEqual(http_client.timeout, tc.TIMEOUT_SECONDS)

from typing import Literal
from translations.models import Translation
from screener.models import Message, Screen
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from decouple import config
from django.conf import settings
from twilio.rest import Client
from django.utils import timezone
from configuration.white_labels import white_label_config


class MessageUser:
    front_end_domain: str = str(config("FRONTEND_DOMAIN", default="http://localhost:3000"))

    cell_account_sid: str = str(config("TWILIO_SID", default=""))
    cell_auth_token: str = str(config("TWILIO_TOKEN", default=""))
    cell_from_phone_number: str = str(config("TWILIO_PHONE_NUMBER", default=""))

    email_from: str = str(config("EMAIL_FROM", default=""))
    email_api_key: str = str(config("SENDGRID", default=""))

    def __init__(self, screen: Screen, lang: str) -> None:
        self.screen = screen
        self.lang = lang

    def should_send(self) -> bool:
        if settings.DEBUG:
            return False

        if self.screen.is_test_data:
            return False

        return True

    def email(self, email: str, send_tests=False):
        if not self.should_send() and not send_tests:
            return

        sg = self._email_client()
        from_name = self._from_name()
        if from_name:
            from_email = Email(self.email_from, from_name)
        else:
            from_email = Email(self.email_from)
        to_email = To(email)  # Change to your recipient
        subject = self._email_subject()
        content = Content("text/html", self._email_body())
        mail = Mail(from_email, to_email, subject, content)

        sg.client.mail.send.post(request_body=mail.get())

        self.log("emailScreen")

    def _email_client(self):
        return sendgrid.SendGridAPIClient(api_key=self.email_api_key)

    def _email_subject(self):
        return self._get_text("subject")

    def _email_body(self):
        words = self._get_text("body") or ""
        url = self._generate_link()

        return words + f' <a href="{url}">{url}</a>'

    def text(self, cell: str, send_tests=False):
        if not self.should_send() and not send_tests:
            return

        self._cell_client().messages.create(
            from_=self.cell_from_phone_number,
            body=self._text_body(),
            to=cell,
        )

        self.log("textScreen")

    def _text_body(self):
        words = self._get_text("body") or ""
        url = self._generate_link()

        return f"{words} {url}"

    def whatsapp(self, cell: str, send_tests=False):
        if not self.should_send() and not send_tests:
            return

        self._cell_client().messages.create(
            from_="whatsapp:" + self.cell_from_phone_number,
            body=self._text_body(),
            to="whatsapp:" + cell,
        )

        self.log("whatsappScreen")

    def _get_text(self, field: Literal["subject", "body", "from_name"]):
        wl_config = white_label_config.get(self.screen.white_label.code) or white_label_config.get("_default")
        comm_config = (getattr(wl_config, "communications", {}) or {}).get("save_results", {}).get(field)

        if comm_config is None:
            return ""

        if isinstance(comm_config, dict) and "_label" in comm_config:
            try:
                trans = Translation.objects.get(label=comm_config["_label"]).get_lang(self.lang)
                if trans and trans.text:
                    return trans.text
            except (Translation.DoesNotExist, AttributeError):
                pass
            return comm_config.get("_default_message", "")

        return str(comm_config)

    def _from_name(self):
        return self._get_text("from_name")

    def _cell_client(self):
        return Client(self.cell_account_sid, self.cell_auth_token)

    def _generate_link(self):
        return f"{self.front_end_domain}/{self.screen.white_label.code}/{self.screen.uuid}/results/benefits"

    def log(self, type: Literal["emailScreen", "textScreen", "whatsappScreen"]):
        self.screen.last_email_request_date = timezone.now()
        self.screen.save()

        Message.objects.create(
            type=type,
            screen=self.screen,
        )

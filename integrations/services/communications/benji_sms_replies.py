"""The fixed replies the Benji SMS inbound webhook sends, and their text (MFB-2439).

Each reply has a translation label and an in-code default. The text is the label's
translation in the conversation's language, else in English, else the default here.
MFB-2444 adds the rows in all 18 languages; until a row exists the default is used and
a warning is logged, so a missing row is visible but never silences a reply.

THE DEFAULTS ARE PROVISIONAL. They are plain-English placeholders so the pipe can be
exercised on staging, not reviewed copy: final wording comes from MFB-2444, with the
sign-offs in MFB-2431.

The stranger reply is bilingual in one text, because nothing is known about a
stranger's language. It is looked up in English only; its row holds both languages.

`{link}` in a reply is replaced with the MyFriendBen address.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

from translations.models import Translation

logger = logging.getLogger(__name__)

LINK_PLACEHOLDER = "{link}"


@dataclass(frozen=True)
class FixedReply:
    label: str
    default: str


STRANGER = FixedReply(
    "benji.sms.stranger",
    "This is MyFriendBen. To find benefits you may qualify for, visit {link}. Reply STOP to end. / "
    "Este es MyFriendBen. Para ver los beneficios para los que puede calificar, visite {link}. "
    "Responda STOP para terminar.",
)
SHARED = FixedReply(
    "benji.sms.shared",
    "This number is linked to more than one set of results. Open the results you want help with "
    "and use Benji there.",
)
REENTRY = FixedReply(
    "benji.sms.reentry",
    "This conversation has ended. To start again, open your results and tap Text with Benji.",
)
STOP = FixedReply(
    "benji.sms.stop",
    "You won't get more texts from Benji. Reply START to turn them back on.",
)
HELP = FixedReply(
    "benji.sms.help",
    "Benji is MyFriendBen's AI assistant. Visit {link} for help. Reply STOP to end.",
)
START_RESUMED = FixedReply(
    "benji.sms.start_resumed",
    "Benji is back. Ask your question any time. Reply STOP to end.",
)
START_REENTRY = FixedReply(
    "benji.sms.start_reentry",
    "You can get texts from Benji again. To start a conversation, open your results and tap "
    "Text with Benji. Reply STOP to end.",
)
PICTURE = FixedReply(
    "benji.sms.picture",
    "Benji can't read pictures yet. Please type what the screen says.",
)


def _label_text(label: str, locale: Optional[str]) -> str:
    """The label's text in `locale`, else in English, else "".

    The same lookup Benji's web context uses (`screener.assistant._translated`): rows
    for other languages start blank or as a placeholder until translated, and neither
    is something to text a person. Not truncated, and line breaks are kept: the copy
    is sent as written.
    """
    # Imported here: screener.assistant pulls in the programs stack, which this module
    # does not otherwise need at import time.
    from screener.assistant import _translated

    translation = Translation.objects.filter(label=label).first()
    return _translated(translation, str(locale or "").lower() or None, max_len=None, flatten=False)


def reply_text(reply: FixedReply, locale: Optional[str] = None) -> str:
    """The text to send for a fixed reply, in `locale` when a translation exists."""
    text = _label_text(reply.label, locale)
    if not text:
        # The label only: no number, body or hash is in reach here.
        logger.warning("Benji SMS fixed reply %s has no translation; using the in-code default.", reply.label)
        text = reply.default
    return text.replace(LINK_PLACEHOLDER, str(settings.FRONTEND_DOMAIN).rstrip("/"))

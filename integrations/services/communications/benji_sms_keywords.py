"""STOP, HELP and START: which inbound texts are opt-out keywords, and whose (MFB-2439).

Two lists, because who answers differs (MFB-1916 proposal v3, decision 4):

CARRIER keywords are Twilio's own. Twilio acts on them before our webhook runs: it
replies itself, and after a STOP it blocks our sends to that number (error 21610), so a
confirmation from us could not be delivered anyway. For these the webhook changes state
and sends nothing.

OUR keywords are the wordings Twilio does not handle: Spanish, and longer English. For
these Twilio does nothing, so the webhook changes state and sends the fixed reply.

A carrier match is deliberately strict (the whole message is exactly the keyword), and
everything looser ("Stop.", "STOP please") counts as ours. Guessing wrong in that
direction is harmless: if Twilio did act, our confirmation fails with 21610 and is
dropped. Guessing wrong the other way would revoke someone in silence.

If Twilio's Advanced Opt-Out is on, the webhook carries ``OptOutType`` and that settles
it: Twilio handled the message, whatever the wording.

Only whole messages match. "stop sending me to that website" is a question, and reaches
the model, whose revocation flag covers wordings no list can (MFB-2440, MFB-2443).

The extended lists are provisional. MFB-2444 owns the final English and Spanish list.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Keyword(str, Enum):
    STOP = "stop"
    HELP = "help"
    START = "start"


@dataclass(frozen=True)
class KeywordMatch:
    keyword: Keyword
    # True when Twilio handled the message itself, so we must not reply.
    carrier: bool
    # True for a word that is a keyword only in context: "yes" re-subscribes a number
    # that opted out, and is an ordinary answer to Benji from one that did not.
    also_plain_text: bool = False


# Twilio's default keyword set for long codes and toll-free numbers.
CARRIER_KEYWORDS: dict[Keyword, frozenset[str]] = {
    Keyword.STOP: frozenset({"stop", "stopall", "unsubscribe", "cancel", "end", "quit", "revoke", "optout"}),
    Keyword.HELP: frozenset({"help", "info"}),
    Keyword.START: frozenset({"start", "yes", "unstop"}),
}

# Compared after `_normalize`: lowercase, no accents, no punctuation, single spaces.
# Letters in every script survive normalizing, so a keyword followed by words in any
# language ("stop 我的福利") is a sentence, not a keyword.
OUR_KEYWORDS: dict[Keyword, frozenset[str]] = {
    Keyword.STOP: frozenset(
        {
            "stop texting",
            "stop texting me",
            "stop messaging me",
            "please stop",
            "stop please",
            "unsubscribe me",
            "remove me",
            "opt out",
            "no more texts",
            "no more messages",
            "alto",
            "parar",
            "pare",
            "detener",
            "basta",
            "cancelar",
            "baja",
            "salir",
            "no mas",
            "no mas mensajes",
        }
    ),
    Keyword.HELP: frozenset({"ayuda", "informacion"}),
    Keyword.START: frozenset({"resume", "start again", "iniciar", "comenzar", "empezar", "reanudar"}),
}

# Keywords that are also things people say in a conversation (see KeywordMatch).
PLAIN_TEXT_WORDS = frozenset({"yes"})

# Anything that is not a letter or a digit, in any script. `\W` is Unicode-aware for
# str patterns; `_` counts as a word character there, so it is listed too.
_NOT_A_WORD = re.compile(r"[\W_]+")


def _normalize(body: str) -> str:
    """Lowercase, accents removed, and every run of punctuation, symbols, emoji and
    space turned into one space. Letters and digits in any script are kept."""
    decomposed = unicodedata.normalize("NFKD", body.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NOT_A_WORD.sub(" ", without_accents).strip()


def classify(body: Optional[str], opt_out_type: Optional[str] = None) -> Optional[KeywordMatch]:
    """The keyword a whole inbound message is, or None for an ordinary text.

    `opt_out_type` is Twilio's `OptOutType` field (STOP, START or HELP), present only
    with Advanced Opt-Out.
    """
    declared = (opt_out_type or "").strip().lower()
    for keyword in Keyword:
        if declared == keyword.value:
            plain = keyword is Keyword.START and (body or "").strip().casefold() in PLAIN_TEXT_WORDS
            return KeywordMatch(keyword, carrier=True, also_plain_text=plain)

    text = body or ""
    exact = text.strip().casefold()
    for keyword, words in CARRIER_KEYWORDS.items():
        if exact in words:
            return KeywordMatch(keyword, carrier=True, also_plain_text=exact in PLAIN_TEXT_WORDS)

    normalized = _normalize(text)
    if not normalized:
        return None
    for keyword in Keyword:
        # A carrier word with punctuation or stray characters around it ("Stop.") lands
        # here: ours to answer, since Twilio only acts on the bare word.
        if normalized in CARRIER_KEYWORDS[keyword] or normalized in OUR_KEYWORDS[keyword]:
            return KeywordMatch(keyword, carrier=False, also_plain_text=normalized in PLAIN_TEXT_WORDS)
    return None

"""Deterministic prose linting — strips recurring LLM-generation artifacts.

Two classes of artifact are fixed here, with no model calls:

1. Stray-space word splits — the classic epub artefact where a word is broken
   by a spurious internal space ("The rain h ad stopped"). We fuse a lowercase
   fragment onto its predecessor when doing so cannot change a legitimate word
   ("had", not "h ad") and does not glue across real word boundaries.

2. Broken / staccato sentences — over-eager full stops and stray mid-word
   capital fragments ("She stared at him.He left." / "he RAN down").

Everything else (suddenly, throat-tightening litanies, em-dash pile-ups) is
guarded by prompt-side craft rules rather than rewritten here, so the prose
voice is never silently rewritten by a linter.
"""

from __future__ import annotations

import re

# ##################################################################
# mid-word stray space
# lowercase fragments glued by a stray space: "h ad" -> "had", "wa s" ->
# "was", "thi s" -> "this". We fuse when neither fragment is a standalone
# common word AND the fused result is not a blocked short word — so legit
# sequences like "he ran" / "it is" are preserved while broken words fuse.
_MIDWORD_SPACE = re.compile(r"\b([a-z]{1,3}) ([a-z]{1,3})\b")

# ##################################################################
# fused sentence boundary
# a period directly followed by a capital with no space. We re-split rather
# than glue, because gluing risks inventing text; splitting only restores
# the spacing the model dropped.
_FUSED_BOUNDARY = re.compile(r"([.!?])([A-Z\"'])")

# ##################################################################
# lowercase stray mid-word capitals
# a lowercase fragment, a space, then an ALL-CAPS run ("he RAN", "She RAN",
# "it WAS") — the misfire where the model restarts a word in capitals. The
# fragment may begin the word ("She" -> "he"+"RAN") or follow other lowercase
# letters ("the" -> "he"+"RAN"). Lowercase the fragment, which restores the
# intended word in context.
_STRAY_CAPITAL = re.compile(r"(?<![A-Za-z])([a-z]{1,3}) ([A-Z]{2,})(?![a-z])")
# word-initial variant: capture the WHOLE word ("She" -> "She"+"RAN"), so the
# replacement can preserve the capital and just fix the fragment.
_STRAY_CAPITAL_WORD = re.compile(r"(?<![A-Za-z])([A-Z][a-z]{1,3}) ([A-Z]{2,})(?![a-z])")

# words that are legitimate as separate tokens — never fuse across these
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "did",
    "do", "does", "for", "go", "had", "has", "have", "he", "her", "hers",
    "him", "himself", "his", "i", "if", "in", "is", "it", "its", "me", "my",
    "no", "nor", "not", "of", "oh", "ok", "on", "once", "one", "or", "our",
    "out", "she", "so", "than", "that", "the", "their", "them", "then", "they",
    "this", "to", "too", "up", "us", "was", "we", "were", "what", "when", "who",
    "why", "you", "your",
}

# words we must never produce by fusing (guard against pathological input)
_FUSE_BLOCKLIST = {"as", "is", "it", "in", "on", "at", "an", "be", "by", "do", "go", "he", "if", "me", "my", "no", "of", "oh", "ok", "or", "so", "to", "up", "us", "we"}


# ##################################################################
# fuse mid-word stray spaces
def _fuse_midword(text: str) -> str:
    def _repl(match: re.Match) -> str:
        first, second = match.group(1), match.group(2)
        # if either fragment is a legit standalone word, leave it alone
        if first in _STOPWORDS or second in _STOPWORDS:
            return match.group(0)
        fused = first + second
        if fused in _FUSE_BLOCKLIST:
            return match.group(0)
        return fused

    previous = None
    while previous != text:
        previous = text
        text = _MIDWORD_SPACE.sub(_repl, text)
    return text


# ##################################################################
# split fused boundaries
def _split_fused(text: str) -> str:
    return _FUSED_BOUNDARY.sub(r"\1 \2", text)


# ##################################################################
# lowercase stray mid-word capitals
def _fix_stray_capitals(text: str) -> str:
    def _repl(match: re.Match) -> str:
        first, second = match.group(1), match.group(2)
        # first is a lowercase mid-word fragment ("the" -> "he"+"RAN"); fuse it
        # onto the restart, lowercased. A stopword fragment is a real word —
        # restore the space with the restart lowercased instead of fusing.
        if first in _STOPWORDS:
            return f"{first} {second.lower()}"
        fused = first + second.lower()
        if fused in _FUSE_BLOCKLIST:
            return match.group(0)
        return fused

    def _repl_word(match: re.Match) -> str:
        # first is a whole word beginning with a capital ("She"+"RAN"); keep the
        # word but lowercase the broken restart so both read correctly.
        first, second = match.group(1), match.group(2)
        return f"{first} {second.lower()}"

    text = _STRAY_CAPITAL_WORD.sub(_repl_word, text)
    text = _STRAY_CAPITAL.sub(_repl, text)
    return text


# ##################################################################
# sanitize prose
# run the deterministic fixes over the section text. order matters: split
# fused boundaries first (so "him.He" -> "him. He") before the mid-word
# fixes, which operate on already-properly-spaced tokens.
def sanitize_prose(text: str) -> str:
    text = _split_fused(text)
    text = _fuse_midword(text)
    text = _fix_stray_capitals(text)
    return text

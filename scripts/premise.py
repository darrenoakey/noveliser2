"""Acceptance-novel invariants shared by the pilot and the full generation run."""

from story_validation import PremiseGuard

PREMISE = (
    "In a late-medieval/early-modern-like land, a fourteen-year-old boy fascinated by a travelling magician "
    "runs away from home to join his show. Expecting actual sorcery, he learns from a competent mentor that "
    "every stage feat is sleight of hand, misdirection or apparatus; supernatural magic is not accepted as "
    "something people can actually perform. The boy discovers that he alone can make a real impossibility "
    "occur, at a concrete personal cost. He must hide his gift precisely among the performers who know every "
    "method for faking it and will spot a violation. Across years he grows into someone consequential through "
    "choices with real costs, including a great act with earned public stakes. His mentor's stagecraft remains "
    "important. The touring route's old floodgates are visibly failing: an influential engineer hides an "
    "unsafe repair to preserve his position, and exposure of the cover-up will cost vulnerable riverside "
    "villages their evacuation window. This material crisis must arise through the troupe's prior choices "
    "rather than a generic witch hunt. No society of secret wizards, hereditary prophecy, or automatic "
    "belief in magic. Relationships have independent goals; any romance grows organically. "
    "The short pilot below is a complete miniature "
    "narrative with a beginning, change and resolution, not a formula sheet."
)

NOVEL_PREMISE = (
    "In a late-medieval/early-modern-like land, a fourteen-year-old boy fascinated by a travelling magician "
    "runs away from home to join his show. Expecting actual sorcery, he learns from a competent mentor that "
    "every stage feat is sleight of hand, misdirection or apparatus; supernatural magic is not accepted as "
    "something people can actually perform. The boy discovers that he alone can make a real impossibility "
    "occur, at a concrete personal cost. He must hide his gift precisely among the performers who know every "
    "method for faking it and will spot a violation. Across years he grows into someone consequential through "
    "choices with real costs, including a great act with earned public stakes. His mentor's stagecraft remains "
    "important. The touring route's old floodgates are visibly failing: an influential engineer hides an "
    "unsafe repair to preserve his position, and exposure of the cover-up will cost vulnerable riverside "
    "villages their evacuation window. This material crisis must arise through the troupe's prior choices "
    "rather than a generic witch hunt. No society of secret wizards, hereditary prophecy, or automatic "
    "belief in magic. Relationships have independent goals; any romance grows organically. "
    "This is a full novel spanning years, from the boy running away to one consequential public act with an "
    "irreversible private price. Do not compress the story into a single week, and do not invent a second real magician."
)

# The brief's earned crisis is the failing floodgates and a concealed unsafe repair.
# Witch-hunt language is rejected even when the model uses it as the supposed alternative.
_WITCH_CRISIS = (
    r"\b(pyre|warlock|witchcraft)\b|\bas (?:a )?witch(?:es)?\b",
    "do not use a pyre, warlock, witchcraft, or 'as a witch' crisis; "
    "the earned crisis is the failing floodgates and the engineer's hidden unsafe repair",
)


def acceptance_guard(protagonist: str) -> PremiseGuard:
    """Return the immutable premise for Darren's illusionist novel."""
    return PremiseGuard(
        protagonist=protagonist,
        required_phrases=("floodgate", "engineer"),
        forbidden=(_WITCH_CRISIS,),
    )

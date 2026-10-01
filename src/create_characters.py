from brain import chat_structured
from craft import CHARACTER_ENGINE_INSTRUCTION
from models import CharactersList, GeneratedCharactersList
from story_validation import plan_with_feedback, validate_characters, with_feedback


# ##################################################################
# create characters
# generate a cast of 3-8 characters with biographies and traits
def create_characters(description: str, plot_type: str, themes: list[str]) -> CharactersList:
    theme_text = ", ".join(themes)

    character_instruction = ""
    description_lower = description.lower()
    if any(word in description_lower for word in ["character", "named", "characters are"]):
        character_instruction = (
            "\n\nIMPORTANT: The description contains specific character names or details. "
            "You MUST use those exact names and details. Do not invent new names if names are provided."
        )

    base_messages = [
        {"role": "system", "content": "You are a character creation expert. Create compelling characters with distinct personalities and clear roles. If character names are provided in the description, you MUST use those exact names."},
        {"role": "user", "content": f"""Create EXACTLY FIVE characters for this story: ONE boy protagonist, ONE older mentor/antagonistic force, THREE supporting characters, including a near-age apprentice peer with independent goals and a person with credible external power who can create material public stakes. Keep each biography under 65 words and every other field concise. Fill EVERY schema field with concrete content; do not leave fields blank. State each character's age when the boy first joins the troupe. A possible romantic interest must be a near-age peer at that time; do not suggest an adult-minor romance. Romance is optional and the other character must have independent goals.

Description: {description}
Plot Type: {plot_type}
Themes: {theme_text}

Create characters with full biographies and personality traits.

{CHARACTER_ENGINE_INSTRUCTION}{CHARACTER_RELATIONAL_INSTRUCTION}{character_instruction}"""},
    ]
    prior: GeneratedCharactersList | None = None

    def build(issues: list[str]) -> GeneratedCharactersList:
        nonlocal prior
        draft = prior.model_dump_json() if prior else ""
        prior = chat_structured(with_feedback(base_messages, issues, draft), GeneratedCharactersList)
        return prior

    return plan_with_feedback(build, validate_characters, "character cast")


CHARACTER_RELATIONAL_INSTRUCTION = """

ALSO, for every protagonist and antagonist (and wants/voice for supporting roles):
- flaw: an OBSERVABLE behavioral flaw that costs them in scenes (what they do, not what they feel).
- voice: distinctive speech - diction, rhythm, what they avoid saying, one verbal habit - so dialogue
  is attributable without tags.
- arc_pressure: the event or choice that tests the Lie and forces the arc.
- relationships: for each key relationship, `other` (EXACT name of another character in this cast),
  `dynamic` (what they are to each other and the unresolved tension) and `pressure` (how it pushes
  the flaw/arc). Every protagonist and antagonist needs at least one."""

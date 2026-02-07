from brain import chat_structured, OPUS_MODEL
from models import CharactersList


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

    messages = [
        {"role": "system", "content": "You are a character creation expert. Create compelling characters with distinct personalities and clear roles. If character names are provided in the description, you MUST use those exact names."},
        {"role": "user", "content": f"""Create 3-8 characters for this story:

Description: {description}
Plot Type: {plot_type}
Themes: {theme_text}

Create characters with full biographies and personality traits.{character_instruction}"""},
    ]
    return chat_structured(messages, CharactersList, model=OPUS_MODEL)

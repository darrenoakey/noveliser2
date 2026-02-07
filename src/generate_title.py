from brain import chat, OPUS_MODEL
from models import Title


# ##################################################################
# generate title
# create a compelling novel title from a story description using opus
def generate_title(description: str) -> Title:
    messages = [
        {"role": "system", "content": "You are a creative title generator for novels. You respond with ONLY the title text - no quotes, no explanation, no preamble, no markdown. Just the title words."},
        {"role": "user", "content": f"Create a compelling, memorable title for this story:\n\n{description}\n\nRespond with ONLY the title. No quotes, no bold, no markdown, no explanation. Just the raw title text."},
    ]
    title_text = chat(messages, model=OPUS_MODEL).strip().strip("\"'*")
    if "\n" in title_text:
        title_text = title_text.split("\n")[-1].strip().strip("\"'*")
    return Title(title=title_text)

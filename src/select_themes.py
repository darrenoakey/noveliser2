from brain import chat_structured, OPUS_MODEL
from models import ThemeSelection


# ##################################################################
# select themes
# choose 2-3 universal literary themes that best fit the story
def select_themes(description: str, plot_type: str) -> ThemeSelection:
    messages = [
        {"role": "system", "content": "You are a literary theme analyst with expertise in identifying universal themes in storytelling."},
        {"role": "user", "content": f"Given this story description and plot type ({plot_type}), select 2-3 universal themes that would best fit this narrative:\n\n{description}"},
    ]
    return chat_structured(messages, ThemeSelection, model=OPUS_MODEL)

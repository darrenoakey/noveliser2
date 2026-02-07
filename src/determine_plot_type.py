from brain import chat_structured, OPUS_MODEL
from models import PlotType


# ##################################################################
# determine plot type
# analyze the story description and classify it into one of booker's seven basic plots
def determine_plot_type(description: str) -> PlotType:
    messages = [
        {"role": "system", "content": "You are a literary analyst specializing in Christopher Booker's Seven Basic Plots. You identify which archetype best fits a given story."},
        {"role": "user", "content": f"Analyze this story description and determine which of the 7 basic plots it best fits:\n\n{description}"},
    ]
    return chat_structured(messages, PlotType, model=OPUS_MODEL)

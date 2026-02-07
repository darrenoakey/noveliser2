from enum import Enum
from pydantic import BaseModel, Field


# ##################################################################
# plot type enum
# christopher booker's seven basic plots - the fundamental story archetypes
class PlotTypeEnum(str, Enum):
    OVERCOMING_THE_MONSTER = "Overcoming the Monster"
    RAGS_TO_RICHES = "Rags to Riches"
    THE_QUEST = "The Quest"
    VOYAGE_AND_RETURN = "Voyage and Return"
    COMEDY = "Comedy"
    TRAGEDY = "Tragedy"
    REBIRTH = "Rebirth"


# ##################################################################
# universal theme
# the 27 universal literary themes that recur across all storytelling
class UniversalTheme(str, Enum):
    LOVE_AND_RELATIONSHIPS = "Love and Relationships"
    GOOD_VS_EVIL = "Good vs Evil"
    COMING_OF_AGE = "Coming of Age"
    DEATH_AND_LOSS = "Death and Loss"
    POWER_AND_CORRUPTION = "Power and Corruption"
    REDEMPTION = "Redemption"
    SURVIVAL = "Survival"
    IDENTITY_AND_SELF = "Identity and Self-Discovery"
    FREEDOM_VS_OPPRESSION = "Freedom vs Oppression"
    SACRIFICE = "Sacrifice"
    JUSTICE = "Justice"
    BETRAYAL = "Betrayal"
    FORGIVENESS = "Forgiveness"
    FAMILY = "Family"
    FRIENDSHIP = "Friendship"
    COURAGE = "Courage"
    LOYALTY = "Loyalty"
    TRUTH_VS_DECEPTION = "Truth vs Deception"
    HOPE = "Hope"
    REVENGE = "Revenge"
    TIME_AND_CHANGE = "Time and Change"
    TRADITION_VS_PROGRESS = "Tradition vs Progress"
    NATURE_AND_HUMANITY = "Nature and Humanity"
    SCIENCE_AND_ETHICS = "Science and Ethics"
    CULTURAL_EXCHANGE = "Cultural Exchange"
    FATE_VS_FREE_WILL = "Fate vs Free Will"
    ISOLATION_AND_BELONGING = "Isolation and Belonging"


# ##################################################################
# character role
# the four types of character roles in a story
class CharacterRole(str, Enum):
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MINOR = "minor"


# ##################################################################
# book status
# tracks the generation state of a novel
class BookStatus(str, Enum):
    ONGOING = "ongoing"
    FINISHED = "finished"
    FAILED = "failed"


# ##################################################################
# title
# the generated title for the novel
class Title(BaseModel):
    title: str = Field(description="A compelling, memorable novel title")


# ##################################################################
# plot type
# the determined plot archetype with reasoning
class PlotType(BaseModel):
    plot_type: PlotTypeEnum = Field(description="The basic plot type that best fits the story")
    reasoning: str = Field(description="Explanation of why this plot type was chosen")


# ##################################################################
# theme selection
# the chosen universal themes for the story
class ThemeSelection(BaseModel):
    themes: list[UniversalTheme] = Field(description="2-3 universal themes that best fit the story")
    reasoning: str = Field(description="Explanation of why these themes were chosen")


# ##################################################################
# character
# a single character with biography and traits
class Character(BaseModel):
    name: str = Field(description="Character name")
    biography: str = Field(description="Character backstory and description")
    role: CharacterRole = Field(description="Role in the story")
    traits: list[str] = Field(description="Personality traits")


# ##################################################################
# characters list
# the full cast of characters for the novel
class CharactersList(BaseModel):
    characters: list[Character] = Field(description="3-8 characters for the story")


# ##################################################################
# writing style
# defines the narrative voice and style for consistency
class WritingStyle(BaseModel):
    style_description: str = Field(description="Overall writing style")
    tone: str = Field(description="Emotional tone of the narrative")
    voice: str = Field(description="Narrative perspective and voice")
    pacing: str = Field(description="Story pacing approach")
    examples: list[str] = Field(description="2-3 example sentences showing the style")


# ##################################################################
# enhanced outline
# the story outline enriched with humor and romance elements
class EnhancedOutline(BaseModel):
    outline: str = Field(description="The enhanced story outline")
    humor_elements: list[str] = Field(description="Humor elements added to the story")
    romance_elements: list[str] = Field(description="Romance elements added to the story")


# ##################################################################
# chapter
# a single chapter plan with story progression details
class Chapter(BaseModel):
    number: int = Field(description="Chapter number")
    title: str = Field(description="A compelling chapter title")
    opening_situation: str = Field(description="State of affairs at chapter start")
    chapter_goal: str = Field(description="What this chapter achieves in the story arc")
    closing_situation: str = Field(description="State of affairs at chapter end")
    key_events: list[str] = Field(description="Major plot points and story beats")


# ##################################################################
# chapter plan
# the complete chapter breakdown for the novel
class ChapterPlan(BaseModel):
    chapters: list[Chapter] = Field(description="All chapters of the novel")


# ##################################################################
# section
# a subsection of a chapter with specific goals
class Section(BaseModel):
    number: int = Field(description="Section number within the chapter")
    goal: str = Field(description="What this section accomplishes")
    key_events: str = Field(description="Specific events and story beats")


# ##################################################################
# section plan
# all sections for a single chapter
class SectionPlan(BaseModel):
    sections: list[Section] = Field(description="All sections of the chapter")


# ##################################################################
# section result
# the generated prose and extracted facts from writing a section
class SectionResult(BaseModel):
    text: str = Field(description="The narrative text")
    new_facts: list[str] = Field(description="New facts established in this section")


# ##################################################################
# epub result
# paths to the final generated epub and cover
class EpubResult(BaseModel):
    epub_path: str = Field(description="Path to the generated EPUB file")
    cover_path: str = Field(description="Path to the cover image")


# ##################################################################
# book metadata
# tracks the full state of a novel generation
class BookMetadata(BaseModel):
    title: str
    description: str
    status: BookStatus
    created_at: str
    updated_at: str
    author: str
    num_chapters: int
    sections_per_chapter: int
    completed_steps: list[str] = []
    current_step: str | None = None
    epub_path: str | None = None
    cover_path: str | None = None

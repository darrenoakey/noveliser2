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
    wound: str = Field(default="", description="Defining past pain (betrayal/abandonment/humiliation) that taught them the world is dangerous")
    lie: str = Field(default="", description="One-sentence false belief built to survive the wound")
    want: str = Field(default="", description="Concrete external goal they pursue in the plot")
    need: str = Field(default="", description="Internal truth they must accept to become whole (often the opposite of the Lie)")
    arc: str = Field(default="", description="Arc type: positive change, flat, disillusionment, or corruption")
    voice_register: str = Field(default="", description="Vocabulary register / diction of this character's speech (e.g. 'terse working-class slang', 'ornate academic formality', 'warm folksy plainspokenness')")
    sentence_style: str = Field(default="", description="Sentence-length and rhythm tendency in dialogue (e.g. 'clipped one-liners', 'long winding qualified sentences', 'blunt declaratives')")
    verbal_tic: str = Field(default="", description="A distinctive verbal habit, catchphrase, or filler this character reaches for (e.g. always says 'right?', over-apologizes, quotes scripture)")


# ##################################################################
# characters list
# the full cast of characters for the novel
class CharactersList(BaseModel):
    characters: list[Character] = Field(description="3-8 characters for the story")


# ##################################################################
# plot
# a single plot line written as a standalone short story
class Plot(BaseModel):
    name: str = Field(description="Short memorable name for this plot line")
    kind: str = Field(default="subplot", description="'primary' for the main plot, 'subplot' otherwise")
    premise: str = Field(default="", description="One-paragraph premise: who wants what, what stands in the way")
    stakes: str = Field(default="", description="What is lost if this plot fails — concrete, personal")
    characters_involved: list[str] = Field(default_factory=list, description="Exact names of characters driving this plot")
    resolution: str = Field(default="", description="How this plot line ultimately resolves")
    story: str = Field(default="", description="The plot written as a standalone short story")


# ##################################################################
# plot set
# all plot lines for the novel; primary first, then subplots
class PlotSet(BaseModel):
    plots: list[Plot] = Field(default_factory=list, description="All plot lines; the primary plot first, then subplots")


# ##################################################################
# character arc
# how a single character changes across the story
class CharacterArc(BaseModel):
    character: str = Field(description="Exact character name")
    before: str = Field(default="", description="Who this character is at the story's start — state of mind, situation, defining behavior")
    after: str = Field(default="", description="Who they are when the story ends — may be better, worse, or dead")
    change_kind: str = Field(default="growth", description="One of: growth, decline, terminal, flat, corruption, redemption")
    journey: str = Field(default="", description="How the plots force this change, step by step")


# ##################################################################
# character arcs
# one arc per named character
class CharacterArcs(BaseModel):
    arcs: list[CharacterArc] = Field(default_factory=list, description="One arc per named character")


# ##################################################################
# writing style
# defines the narrative voice and style for consistency
class WritingStyle(BaseModel):
    style_description: str = Field(description="Overall writing style")
    tone: str = Field(description="Emotional tone of the narrative")
    voice: str = Field(description="Narrative perspective and voice")
    pacing: str = Field(description="Story pacing approach")
    examples: list[str] = Field(description="2-3 example sentences showing the style")
    pov: str = Field(default="", description="Structured point of view, e.g. 'first person', 'third limited', 'third omniscient', 'second person'")
    tense: str = Field(default="", description="Structured narrative tense, e.g. 'past' or 'present'")


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
    scene_type: str = Field(default="scene", description="'scene' (proactive: goal/conflict/disaster) or 'sequel' (reactive: reaction/dilemma/decision)")
    disaster: str = Field(default="", description="The setback that ends a scene, or the hard decision/new risk that ends a sequel")
    intensity: str = Field(default="medium", description="Pacing intensity: 'fast'/'tense' (action, danger, confrontation — write shorter and leaner), 'medium' (default), or 'slow'/'reflective' (aftermath, introspection, emotional processing — write longer and more expansive)")


# ##################################################################
# section plan
# all sections for a single chapter
class SectionPlan(BaseModel):
    sections: list[Section] = Field(description="All sections of the chapter")


# ##################################################################
# fact
# a single canonical fact about a subject in the story
class Fact(BaseModel):
    subject: str = Field(description="The entity the fact is about (character, place, object) - use the canonical name")
    attribute: str = Field(description="Short snake_case attribute name (e.g. 'breed', 'eye_color', 'occupation', 'location')")
    value: str = Field(description="The value of the attribute, kept short (e.g. 'golden retriever', 'blue', 'doctor')")
    first_seen: str = Field(default="", description="Where this fact was first established, e.g. 'ch1.s2'")


# ##################################################################
# section result
# the generated prose for a section. new_facts is retained for backward
# compatibility with checkpoint files written by the old fact-ledger pipeline;
# the current retrieval-memory pipeline leaves it empty.
class SectionResult(BaseModel):
    text: str = Field(description="The narrative text")
    new_facts: list[Fact] = Field(default_factory=list, description="(legacy) facts established in this section; unused by the retrieval-memory pipeline")


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

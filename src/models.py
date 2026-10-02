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
# relationship
# a directed pressure between this character and another named character
class Relationship(BaseModel):
    other: str = Field(description="Exact name of the other character")
    dynamic: str = Field(description="What this person is to them (ally, rival, lover, mentor, victim...) and the unresolved tension")
    pressure: str = Field(default="", description="How this relationship pushes on the character's flaw/arc, or changes over the story")


# ##################################################################
# character
# a single character with biography and traits
class Character(BaseModel):
    age_at_start: int | None = Field(default=None, description="Age when the protagonist joins the troupe; later time jumps are explicit")
    name: str = Field(description="Character name")
    biography: str = Field(description="Character backstory and description")
    role: CharacterRole = Field(description="Role in the story")
    traits: list[str] = Field(description="Personality traits")
    wound: str = Field(default="", description="Defining past pain (betrayal/abandonment/humiliation) that taught them the world is dangerous")
    lie: str = Field(default="", description="One-sentence false belief built to survive the wound")
    want: str = Field(default="", description="Concrete external goal they pursue in the plot")
    need: str = Field(default="", description="Internal truth they must accept to become whole (often the opposite of the Lie)")
    arc: str = Field(default="", description="Arc type: positive change, flat, disillusionment, or corruption")
    flaw: str = Field(default="", description="Observable behavioral flaw that costs them in scenes (not just a feeling)")
    voice: str = Field(default="", description="Distinctive speech: diction, rhythm, what they avoid saying, a verbal habit")
    arc_pressure: str = Field(default="", description="The event or choice that forces the arc: how the Lie is tested and finally abandoned or embraced")
    relationships: list[Relationship] = Field(default_factory=list, description="Key relationships with other named characters")


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
    pov_character: str = Field(default="", description="Exact name of the character whose pursuit drives this chapter")
    cause_from_previous: str = Field(default="", description="The specific consequence of the previous chapter that forces this chapter (empty only for chapter 1)")
    pursuit: str = Field(default="", description="What the actor concretely tries to achieve in this chapter")
    opposition: str = Field(default="", description="Specific person/force/obstacle opposing the pursuit")
    stakes: str = Field(default="", description="What is lost, and by whom, if the pursuit fails")
    choice: str = Field(default="", description="The hard choice the actor makes between competing options")
    cost: str = Field(default="", description="What the choice costs, irreversibly")
    reversal: str = Field(default="", description="The reversal or revelation that changes what the actor believes or must do")
    value_before: str = Field(default="", description="Value state (e.g. trust, safety, hope, knowledge) at chapter start")
    value_after: str = Field(default="", description="Value state at chapter end; must differ from value_before")
    setups: list[str] = Field(default_factory=list, description="Short ids of promises/clues/objects planted here (e.g. 'silver-key')")
    payoffs: list[str] = Field(default_factory=list, description="Ids of EARLIER setups paid off here")
    subplot: str = Field(default="", description="Name of the subplot/relationship/mystery thread this chapter advances, if any")
    subplot_change: str = Field(default="", description="How that thread changes in this chapter")
    open_question: str = Field(default="", description="The question the reader needs answered after this chapter (empty only for the final chapter)")


# ##################################################################
# chapter plan
# the complete chapter breakdown for the novel
class ChapterPlan(BaseModel):
    chapters: list[Chapter] = Field(description="All chapters of the novel")
    central_question: str = Field(default="", description="The dramatic/mystery question the whole novel answers")
    subplots: list[str] = Field(default_factory=list, description="Names of subplot/mystery threads; each must be advanced by at least one chapter's subplot field")


# ##################################################################
# schedule contract
# A model-authored, finite commitment ledger for a later chapter planner.
class ScheduledObligation(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,47}$", description="Stable machine identifier")
    entity_anchor: str = Field(min_length=8, max_length=160,
                               description="Concrete identity shared by the plant and payoff")
    plant_chapter: int = Field(ge=1)
    plant_anchor: str = Field(min_length=8, max_length=240,
                              description="Exact on-page plant action")
    payoff_chapter: int = Field(ge=2)
    payoff_anchor: str = Field(min_length=8, max_length=240,
                               description="Exact later on-page payoff action using the same entity")


class ScheduledHandoff(BaseModel):
    from_chapter: int = Field(ge=1)
    to_chapter: int = Field(ge=2)
    consequence_anchor: str = Field(min_length=8, max_length=240,
                                    description="Concrete consequence that forces the next chapter")


class ScheduleContract(BaseModel):
    obligations: list[ScheduledObligation] = Field(min_length=1, max_length=3)
    handoffs: list[ScheduledHandoff] = Field(description="One adjacent handoff for every chapter boundary")


# ##################################################################
# section
# a subsection of a chapter with specific goals
class Section(BaseModel):
    number: int = Field(description="Section number within the chapter")
    goal: str = Field(description="What this section accomplishes")
    key_events: str = Field(description="Specific events and story beats")
    scene_type: str = Field(default="scene", description="'scene' (proactive: goal/conflict/disaster) or 'sequel' (reactive: reaction/dilemma/decision)")
    disaster: str = Field(default="", description="The setback that ends a scene, or the hard decision/new risk that ends a sequel")
    pov_character: str = Field(default="", description="Exact name of the POV character")
    cause: str = Field(default="", description="What from the previous section forces this one (empty only for the chapter's first section)")
    obstacle: str = Field(default="", description="Specific opposition met in this section")
    choice: str = Field(default="", description="The decision/dilemma resolution the POV makes")
    cost: str = Field(default="", description="What the choice costs")
    value_before: str = Field(default="", description="Value state at section start")
    value_after: str = Field(default="", description="Value state at section end; must differ from value_before")
    setups: list[str] = Field(default_factory=list, description="Ids of promises/clues planted here")
    payoffs: list[str] = Field(default_factory=list, description="Ids of earlier setups paid off here")
    next_obligation: str = Field(default="", description="What the next section must address because of how this one ends (empty for the chapter's last section)")


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

# ##################################################################
# strict generation schemas
# legacy checkpoints accept absent causal fields, but new Ollama JSON output
# must fill them rather than treating default empty strings as a valid suggestion.
class GeneratedCharacter(Character):
    age_at_start: int = Field(ge=8, le=100)
    wound: str = Field(min_length=5)
    lie: str = Field(min_length=5)
    want: str = Field(min_length=5)
    need: str = Field(min_length=5)
    arc: str = Field(min_length=5)
    flaw: str = Field(min_length=5)
    voice: str = Field(min_length=5)
    arc_pressure: str = Field(min_length=5)
    relationships: list[Relationship] = Field(min_length=1)


class GeneratedCharactersList(CharactersList):
    characters: list[GeneratedCharacter] = Field(min_length=3, max_length=5)


class GeneratedChapter(Chapter):
    cause_from_previous: str = Field(min_length=5)
    pov_character: str = Field(min_length=2)
    pursuit: str = Field(min_length=5)
    opposition: str = Field(min_length=5)
    stakes: str = Field(min_length=5)
    choice: str = Field(min_length=5)
    cost: str = Field(min_length=5)
    reversal: str = Field(min_length=5)
    value_before: str = Field(min_length=3)
    value_after: str = Field(min_length=3)
    open_question: str = Field(min_length=5)
    subplot: str = Field(min_length=2)
    subplot_change: str = Field(min_length=5)
    setups: list[str] = Field(description="Only short stable identifiers, e.g. red-thread; empty if none")
    payoffs: list[str] = Field(description="Exact IDs from earlier chapters, no explanations; empty if none")


class GeneratedChapterPlan(ChapterPlan):
    chapters: list[GeneratedChapter]
    central_question: str = Field(min_length=5)
    subplots: list[str] = Field(min_length=1, max_length=3)


class GeneratedSection(Section):
    cause: str = Field(min_length=5)
    next_obligation: str = Field(min_length=5)
    pov_character: str = Field(min_length=2)
    obstacle: str = Field(min_length=5)
    choice: str = Field(min_length=5)
    cost: str = Field(min_length=5)
    disaster: str = Field(min_length=5)
    value_before: str = Field(min_length=3)
    value_after: str = Field(min_length=3)


class GeneratedSectionPlan(SectionPlan):
    sections: list[GeneratedSection]

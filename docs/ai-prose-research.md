# Why generated fiction feels generated — research and revision guide

Research date: 17 November 2026. Scope: English-language fiction, especially a fantasy narrative generated in sections. This is a craft report, **not an AI-authorship detector**.

## Executive findings

- The problem is usually **default rhetorical behavior replacing dramatic particularity**: balanced clauses where perception would be uneven; thematic explanation where an action would matter; everybody speaking polished wisdom instead of trying to get something.
- Tricolon, anaphora, antithesis, metaphor, summary and aphorism are legitimate literary tools. Their repeated, unearned deployment makes them conspicuous. Removing every example would impoverish human writing too.
- Controlled research supports homogenization and measurable model-specific stylistic tendencies. It does **not** establish that a particular metaphor or em dash proves machine authorship, nor an optimal number of tricolons per thousand words.
- Positive instructions matter: define who perceives, what they know, what they want, what they physically do, how their vocabulary was acquired, and what changes because of the encounter. A long negative blacklist alone leaves the model no usable conception of the desired prose.
- Revise from quoted local evidence, preserve good exceptions, and compare against the original. Repeatedly asking for “more literary,” “more vivid,” or “more human” can increase the very ornament and generic emotional explanation being removed.

## 1. Research method and source confidence

Actual Google searches were run through the installed `web_driver.WebDriver` client driving Chrome. Search-result links were followed; the source pages' rendered body text was inspected. Search snippets alone were not treated as evidence. The ten searches included:

1. `AI generated fiction tricolon anaphora not X but Y writing`
2. `Doshi Hauser generative AI enhances individual creativity reduces collective diversity 2024 Science Advances`
3. `LLM creative writing homogenization linguistic style fiction study`
4. `AI fiction aphoristic dialogue metaphor overload telling summaries writing criticism`
5. `generative AI creative writing prompting revision specific feedback Self Refine study`
6. `Doshi Hauser 2024 293 600 short stories creativity 8.1 9 percent`
7. `LLM writing stylistic preferences human writing corpus tricolon parallelism study`
8. `Ursula Le Guin steering craft prose rhythm sentence sound repetition`
9. `George Orwell politics English language stale metaphors never use metaphor`
10. `fiction dialogue subtext not on the nose writing advice character voice`

Source register below distinguishes experiments, observational comparisons, scholarly synthesis, editorial advice and anecdotes. PubMed initially displayed a browser-check interstitial, so it was not relied on; the full Science Advances article itself loaded. No claim here depends on an inaccessible Atlantic article surfaced by Google. Source text captures are temporary research artifacts in `/tmp/ai-prose-research/`, not a repository dependency.

### Empirical and scholarly sources

**[E1] Anil R. Doshi and Oliver P. Hauser, “Generative AI enhances individual creativity but reduces the collective diversity of novel content,” Science Advances 10(28), 12 July 2024.** [Full article and DOI](https://www.science.org/doi/10.1126/sciadv.adn5290); [UCL's contemporary summary](https://www.ucl.ac.uk/news/2024/jul/ai-boosts-individual-creativity-expense-less-varied-content).

Randomized online experiment: 293 writers wrote eight-sentence stories; conditions offered no AI ideas, one idea, or up to five ideas. A separate 600 evaluators assessed stories. AI access improved evaluated creativity, writing and enjoyment, particularly for less creative writers; AI-assisted stories were also more similar to one another. Crucial distinction: writers received **ideas**, not a fully generated novel. The authors explicitly limit generalization from short stories, fixed prompts and noninteractive use. This is good evidence for an anchoring/diversity problem, not evidence for specific sentence-level “tells,” and not proof that every AI-assisted story is worse.

**[E2] Alex Reinhart et al., “Do LLMs write like humans? Variation in grammatical and rhetorical styles.”** [Inspected arXiv HTML](https://arxiv.org/html/2410.16107v1); [journal DOI surfaced by Google](https://www.pnas.org/doi/10.1073/pnas.2422455122).

Parallel human/model corpora and Biber-derived linguistic features identify systematic differences across Llama 3 variants and GPT-4o variants. The inspected Results section reports instruction-tuned models favoring present participial clauses, subject “that” clauses, nominalization and phrasal coordination: a dense, noun-heavy style. Different model families also have different “house styles.” Instruction tuning appears important, so “all models simply write the statistical average” is inadequate as a complete explanation. The paper also cautions about generalization across models/registers. This was not a controlled test of fantasy tricolon quotas; do not borrow its classifier results as an accuracy claim for a homegrown prose checker. The HTML page carries a revised manuscript date despite the versioned URL; cite title/URL rather than pretending every displayed section is frozen to the identifier's first date.

**[E3] “The Homogenizing Effect of Large Language Models on Human Expression and Thought.”** [Inspected scholarly synthesis](https://arxiv.org/html/2508.01491v2).

A synthesis across linguistic style, perspectives and reasoning, not a new single fiction experiment. It describes mechanisms by which training, alignment, dominant representations and recursive reuse can narrow variation; identity prompting can also yield caricature rather than authentic diversity. Useful implication: differentiating characters requires private experience, goals and ways of noticing, not merely attaching demographic labels or accents. Its broad conceptual arguments should not be mislabeled causal proof for a particular narrative device.

**[E4] Aman Madaan et al., “Self-Refine: Iterative Refinement with Self-Feedback,” NeurIPS 2023.** [Inspected conference abstract](https://neurips.cc/virtual/2023/poster/71632).

Uses an initial answer, specific feedback and revision by the same model. Across seven tasks the abstract reports improvements over one-step generation, including dialogue generation. This supports testing a feedback/revision workflow; it does **not** establish a 20% improvement in novel quality or guarantee self-criticism is correct. A bounded revision pass with independent checks is an engineering recommendation, not a published fiction-specific result.

**[E5] Tuhin Chakrabarty and Paramveer S. Dhillon, “Can Good Writing Be Generative? Expert-Level AI Writing Emerges through Fine-Tuning on High-Quality Books,” 26 January 2026 preprint.** [Inspected paper](https://arxiv.org/html/2601.18353v1).

Experiment involving 28 MFA writers emulating 50 authors, expert and lay judgments, and prompting versus fine-tuning. Its abstract reports experts preferred human writing in 82.7% of in-context-prompting comparisons, but preferred AI in 62% after fine-tuning; lay judges consistently preferred AI. This is an important counterweight to universal claims about “AI prose”: evaluation depends on audience, task and model treatment. It is a preprint, author-emulation experiment and not evidence that a style prompt alone achieves expert long-form fiction. No recommendation to copy copyrighted authors' complete works follows from it.

### Rhetorical analysis and craft advice — not controlled experiments

**[C1] Colin Gorrie, “Why ChatGPT writes like that: A rhetorical analysis of AI ‘slop’,” 10 July 2025.** [Inspected essay](https://www.deadlanguagesociety.com/p/rhetorical-analysis-ai).

Most directly applicable source. Discusses compulsive parallelism, explicit-negation antithesis, the rule of three/tricolon, and human historical precedents. His key distinction is robotic consistency versus taste about when to deploy a technique. This is a linguist's rhetorical analysis with examples, not a representative frequency study. The essay's account of why models choose these forms should not be elevated to experimentally isolated training causation.

**[C2] George Orwell, “Politics and the English Language.”** [Inspected complete essay, Orwell Foundation](https://www.orwellfoundation.com/the-orwell-foundation/orwell/essays-and-other-works/politics-and-the-english-language/).

Critiques stale imagery, ready-made phrases, abstraction and language that ceases to evoke a concrete object. Useful revision questions: what exactly is meant; does the image clarify it; can unnecessary language go? Its principal target is political prose, not a universal fiction rulebook. Orwell's own final exception to his rules argues against mechanical prohibition.

**[C3] K. M. Weiland, “Get Rid of On-the-Nose Dialogue: 3 Ways to Write Dialogue With Subtext.”** [Inspected craft article](https://www.helpingwritersbecomeauthors.com/get-rid-of-on-the-nose-dialogue/).

Defines on-the-nose dialogue as explicitly stating thoughts, feelings or wants instead of permitting inference. Discusses what remains unsaid and implication in dialogue. This supports a positive dialogue-revision method; it does not prove all direct statements are bad or that all indirect dialogue is better.

**[C4] Nicole Bianchi, “3 Powerful Writing Exercises from Ursula K. Le Guin's Steering the Craft.”** [Inspected secondary discussion](https://nicolebianchi.com/ursula-k-le-guin-steering-the-craft/).

Discusses hearing prose, varying sentence rhythms and practicing narrative sound. This is a secondary account quoting/discussing Le Guin, not a claim that the complete book was read for this assignment. Reading aloud and controlled revision exercises are more useful than optimizing for random sentence-length variance.

**[A1] r/WritingWithAI, “Some AI ‘tells’.”** [Inspected thread](https://www.reddit.com/r/WritingWithAI/comments/1bvj2k8/some_ai_tells/).

Practitioner observations include unnecessary wrap-ups in mid-scene snippets, repeated bodily reactions, redundant internality, stereotyped descriptions, excessive positivity and weak conflict. These are useful hypotheses and recognizable editorial complaints, **not validated diagnostics**. A crowd repeating a claim is not a frequency study.

## 2. Why these particular patterns grate

The user's requested categories are tricolons, repeated anaphora, not-X-but-Y antithesis, aphoristic dialogue, summaries/metaphor overload and homogenization. The exact user-supplied lines are discussed separately below. **Other before/after sentences in the category subsections are constructed demonstrations, not quotations from a generated book.** Alternatives illustrate possible improvements, not a mandatory plain style.

### Tricolons: three beats on automatic

A tricolon is a three-part parallel structure, not simply every list containing three objects. “Salt, rope and a knife” may be inventory. “He carried grief, guilt and the weight of tomorrow” packages emotion as a balanced performance.

- **Before:** “The bell promised justice, demanded sacrifice, and offered redemption.”
- **Possible revision:** “Mara pulled the rope again. Below her, the men at the gate stopped arguing over whose son would go.”
- **Why:** the reader gets an action, a cost and a social response instead of three thematic labels.
- **Keep it when:** a ceremony, spell, proclamation, joke or character's rehearsed speech needs three deliberate beats. Ask whether each member adds distinct information and whether the climax earns the cadence.

A third item should not exist merely to complete the rhythm. But deleting every third item would turn a taste problem into a counting ritual. [C1]

### Repeated anaphora: emotion announced by repeated openings

Anaphora repeats initial words across adjacent clauses or sentences. It can be incantatory or obsessive; it becomes predictable when every emotional peak receives the same ladder.

- **Before:** “She remembered the furnace. She remembered the screams. She remembered the hand she had let go.”
- **Possible revision:** “The tongs struck the hearth. She dropped them. For a moment she was holding her brother's hand again, and his fingers were slipping.”
- **Why:** a present sensory trigger interrupts a task; recollection has a specific pressure instead of becoming a generic rhetorical list.
- **Keep it when:** the narrator intentionally chants, accuses, counts, prays or rehearses a thought. Repetition can enact fixation. Look for repeated *function* across scenes as well as repeated words. [C1, C4]

### Not X but Y: the narrator constantly correcting a claim nobody made

Explicit-negation antithesis offers instant gravitas: deny a banal interpretation, substitute a “deeper” one. It can manufacture a false distinction and keep the author between the reader and the scene.

- **Before:** “It was not courage that kept him at the door, but love.”
- **Possible revision:** “He could still reach the stairs. Then his daughter coughed inside the room.”
- **Why:** the conflict is embodied in available action. Courage and love need not be mutually exclusive.
- **Keep it when:** the correction matters factually, the speaker is arguing, or the reversal genuinely alters understanding. “Not the north stair. The west one.” is practical correction, not pseudo-profundity. [C1]

### Aphoristic dialogue: everybody becomes the same essayist

- **Before:** “‘A crown is only a wound the kingdom has learned to worship,’ the porter said.”
- **Possible revision:** “‘You'll need to leave that outside.’ The porter nodded at the crown. ‘It catches on the lintel.’”
- **Why:** rank, attitude and power become specific to this exchange. A porter may absolutely be philosophical; the issue is whether the utterance comes from this person pursuing this objective, rather than the model supplying a quotable theme.

Give speakers different tactics: one asks the price, one changes the subject, one answers only what is safe, one talks while doing a job. Let an admission cost something. Allow banal lines, misunderstandings and occasional direct speech. Not every exchange needs a maxim, a therapist's validation or a completed emotional reconciliation. [C3, A1]

Contemporary phrases such as “hold space,” “your feelings are valid,” “healing journey,” “set boundaries” or “process your trauma” are **contextual review examples**, not an empirically verified universal AI phrase list. They may fit a modern counselor perfectly; in secondary-world fantasy they need an established cultural register. Replacing them with faux-archaic thesaurus language is not a solution.

### Summary creep and repeated thematic explanation

- **Before:** “They crossed the flooded yard together, learning that trust was not given but forged through shared adversity.”
- **Possible revision:** “At the last flooded step, Iven gave her his good hand. This time she took it.”
- **Why:** a changed relationship is inferred from a meaningful choice. A later sentence explaining that they had learned trust would repeat the information.

Summary is indispensable for elapsed time, routine travel, perspective and compression. The target is **unearned interpretive summary**, especially after dialogue already communicated the emotion, or at every section boundary. When generating a middle section, say explicitly that the narrative continues: do not manufacture a concluding lesson. [A1, C2]

### Metaphor overload: too many pictures, none allowed to develop

- **Before:** “Fear bloomed in her chest, an icy river carrying the shattered glass of yesterday through the cathedral of her heart.”
- **Possible revision:** “She wrapped both hands around the cup. The tea slopped over anyway.”
- **More lyrical alternative:** “The bell's crack showed black through the bronze. She kept looking at it instead of his face.”
- **Why:** choose a perceivable detail or a coherent image that carries the character's attention. Avoid changing the conceptual domain repeatedly in one emotional beat.

Do not confuse imagery with simile. A precise object can do more than an abstract feeling given several decorative vehicles. A bell founder may notice seams, porosity and cooling bronze; a debt collector may notice the resale value of the same bell. Image choice is a voice decision. Metaphor density should follow the agreed narrative mode, not a universal “one per page” law. [C2, C4]

### Homogenization: the same good taste, values and syntax everywhere

Characters are not differentiated merely because one uses contractions and one does not. Ask what each notices first, what they misread, what they are ashamed to name, what comparison they would never make, and what they want from this listener.

- **Generic:** “The city was a tapestry of resilience, every alley holding a story.”
- **Possible revision:** “The tax clerk counted six new shutters on Rope Street. None had been declared.”
- **Why:** location, occupation, selective perception and prospective conflict arrive together. It is not “better” in every book; it is more particular for this focalizer.

Do not replace homogenization with caricatured dialect or identity stereotypes. The controlled evidence concerns anchoring and aggregate convergence [E1]; the broader synthesis highlights identity-prompting risks [E3]. Neither proves a demographic label creates an authentic voice.

### Close reading of the user's exact examples

These lines were supplied verbatim by the parent after the initial research. Their surrounding scenes are unknown, so the alternatives below are **conditional editorial possibilities**, not claims about the actual characters, plot or authorial intention.

> “Elena looked at the rain, at her laptop, at the empty hours stacked ahead like unplayed measures.”

The repeated `at` supplies parallel rhythm; rain → laptop → abstract future creates a three-beat escalation. “Stacked” and “unplayed measures” also ask the reader to combine spatial and musical conceptions of time. This could work if Elena experiences time musically and the scene earns that cadence. The defect is not that a sentence contains three things. If nearby prose repeatedly uses the same escalation into a metaphor, a more immediate version might be: **“Rain blurred the window. Elena opened her laptop, then closed it without waking the screen.”** That alternative invents a behavior and must not be adopted if it contradicts the scene. A more conservative compression is **“Elena looked from the rain to her laptop. She had hours to fill.”** It sacrifices the musical register; preserve the original image if that register matters.

> “We're not changing the ending, Elena. We're just filling the middle.”

This is a plausible reassurance, minimization or euphemism for interference. It is **not automatically bad dialogue**. The repeated negative-correction shape becomes the problem if every speaker uses it. If the intention is an evasive practical proposal: **“The ending stays, Elena. Can we work on the middle?”** If the pressure is more controlling: **“Leave the ending. Open the middle section.”** Those imply different power relations; choose using the scene, not the checker. The original may be best if the speaker is consciously selling an intrusion as something harmless.

> “I'm not calling it collaboration. I'm calling it a documented structural consultation.”

The contrast may deliberately expose bureaucratic self-protection or comic hair-splitting. “Documented structural consultation” can be character-revealing diction, not generic AI abstraction. If that legalistic distinction matters, **keep it**. To reduce repeated framing while retaining the distinction: **“Put ‘structural consultation’ in the record. I haven't agreed to a collaboration.”** This adds an instruction and an explicit agreement issue, so verify the actual intention before adoption. A minimally changed version is **“I'd call it a documented structural consultation.”** It is less adversarial and loses the joke's corrective rhythm; that loss may be unacceptable.

> “You're not debating. You're defending. There's a difference.”

The mirrored clauses and appended explanation create a ready-made confrontation. “There's a difference” may explain what the contrast already implies. A small, meaning-preserving edit is **“You're defending it.”** If the scene supports a specific unaddressed question, use it instead: **“You still haven't answered the question.”** That is not semantically identical: defensiveness does not necessarily mean failing to answer. The original might suit a character who habitually issues judgments; a different speaker might retreat, mock, change the subject or ask what evidence would persuade Elena.

**Pattern-level conclusion:** three supplied dialogue lines employ correction/relabeling, although their intentions could differ substantially. The useful revision question is whether the repetition belongs to one character's tactic or leaks across otherwise distinct characters. Do not strip out the bureaucratic joke, musical viewpoint or power dynamic simply to lower a syntax counter. A reviewer needs neighboring paragraphs and speaker identities before making that call.

## 3. Concrete prompt recipes

These are proposed production recipes, **not scientifically validated guarantees**. Use the actual story facts and a short positive sample written for this book. Avoid requesting imitation of a named living writer.

### A. Persistent style specification — establish before drafting

```text
Create a reusable style specification for this book, not a sales description.
State operational choices and give one original positive example for each:
- POV and knowledge boundary; narrative distance and permitted shifts.
- Tense, register, diction and the focalizer's occupational/private vocabulary.
- Rhythm baseline and how it changes under danger, hesitation and reflection.
- Concrete things this focalizer notices; image domains they plausibly know.
- Dialogue tactics for each principal speaker: want, evasion, status behavior,
  syntax, subjects avoided. Do not reduce voice to accents or identity labels.
- Summary policy: what to compress and what consequential moments to dramatize.
- Figurative-language policy: grounded images; no competing image domains
  unless deliberately motivated. Preserve earned lyricism.
- Rhetorical exceptions: where ceremony, obsession or a public argument may
  justify triads, repetition or antithesis.
Include short before/after examples specific to this setting.
Do not describe the target merely as evocative, nuanced, cinematic or human.
```

Persist this object, not just its `name` or `description`. Inject its useful fields into each prose call; retain compatibility when resuming older books. Keep book facts and style preferences distinguishable: changing a cadence preference must not alter a character's history.

### B. Scene drafting — positive constraints first

```text
Write the next continuous scene using the saved style specification.
POV: [name]. They know [facts], wrongly believe [belief], and cannot know [facts].
Immediate physical objective: [objective]. Obstacle: [person/material/deadline].
Private pressure they will not state aloud: [pressure].
Begin with [ongoing task], not a thematic introduction.
Let dialogue pursue incompatible local wants; do not make every speaker a
philosopher or resolve their conflict through validation.
Choose concrete details through this POV's experience. Let rhythm follow
attention and action, not a fixed short/long sentence alternation.
At the end, [specific changed circumstance/decision]. This is a middle scene:
no closing moral, emotional recap or preview of the coming chapter.
Use literary devices when they earn their place; avoid repeating one
parallel-clause shape merely to create emphasis.
```

### C. Evidence-first diagnostic pass — no rewrite yet

```text
Read this scene and its style specification. Diagnose at most five material
craft problems. For each return:
1. exact quotation and location;
2. the effect on this scene or character, not “sounds AI”;
3. a specific revision operation;
4. any reason to preserve the original.
Review clustered triads, repeated openings, unnecessary not-X-but-Y corrections,
aphoristic dialogue, duplicated emotional explanation, competing metaphors,
and knowledge/voice drift. A device's presence alone is not a defect.
If none is harmful, return no changes. Identify one passage worth preserving.
Do not invent quotations, new facts or research-based frequency thresholds.
```

### D. Bounded local revision

```text
Revise only the supported problems in the diagnostic notes.
Preserve plot events, chronology, named facts, character knowledge, tone,
POV/tense, and deliberate strong passages. Do not add backstory or new imagery
merely to decorate the rewrite. Prefer specific perception, consequential
physical action, or subtext where the original explains a theme.
Keep summary where compression serves pacing. Keep earned repetition.
Return the revised scene and a brief change log mapping edits to quotations.
Do not append an explanation of the scene's moral.
```

Run continuity and style checks on the candidate, then compare it to the original. A rewrite that loses the deadline, clue or character's motive is worse even if its antithesis count falls. [E4 supports trying refinement, not blind acceptance.]

### E. Voice contrast test

```text
For each speaker, quote two lines that could be swapped with another speaker
without affecting voice. Explain whether this is actually a problem in context.
Revise only genuinely interchangeable lines using the speaker's immediate aim,
relative power, private knowledge and habitual way of noticing.
Do not manufacture dialect, catchphrases or aphorisms as identity badges.
```

## 4. Checking without turning taste into a brittle lint gate

**No inspected source provides a validated safe limit for em dashes, triads, metaphors or not-X-but-Y constructions per 1,000 words.** Do not invent one and attribute it to this research.

Useful engineering instrumentation:

- Record raw counts, word-normalized rates and **quoted contexts**. Normalize comparable passages; a 150-word opening is not a stable basis for whole-book density claims.
- Separate literal inventory lists from rhetorical tricolons. Regex cannot reliably parse both.
- Separate factual corrections, dialogue and narration when counting antithesis. Include variants such as “wasn't X; it was Y” in diagnostic search without declaring every match a defect.
- Look for repeated sentence stems and repeated *paragraph functions*: a final moral after every exchange may matter more than punctuation.
- Track image-domain collisions and character-voice collapse by human/semantic review. Regex cannot establish metaphor quality or subtext.
- Compare scenes and characters, not only the aggregate. A deliberate incantation is locally repetitive and may be excellent; identical incantatory prose in every viewpoint suggests a house-style leak.

If an implementation needs initial review triggers, **three adjacent identical sentence openings** or **two explicit not-X-but-Y constructions in a short scene** can be configurable, unvalidated prompts for inspection. They are not rejection criteria, not recommended artistic maximums and not evidence of AI authorship. There is no corresponding defensible universal em-dash quota. Calibrate against manually reviewed target prose and preserve overrides.

Keep mechanical tests hard only for things that truly are mechanical: nonempty output, valid structure, preserved required fields, exact saved quotation matching, no missing chapters, and continuity checks with clear evidence. Craft findings should generate a review brief, not silently destroy a lyrical voice.

## 5. Recommended production and evaluation sequence

1. Save a detailed book-specific style profile plus knowledge/continuity state.
2. Draft a scene with a concrete objective, opposition and consequential ending.
3. Run inexpensive repeat-pattern diagnostics; collect contexts rather than scores.
4. Ask for a short evidence-first critique; include legitimate exceptions.
5. Make at most one targeted automatic revision by default. Escalate specific unresolved defects instead of endlessly “humanizing.”
6. Check names, chronology, knowledge boundaries, objectives and consequences against the original and established facts. Preserve the original candidate and change log.
7. Read consecutive scenes aloud (or listen to rendered audio). Check monotonous cadence, identical voices and false finality at generated section seams.
8. Evaluate blinded A/B excerpts on **specificity, dramatic causality, distinct voice, rhythmic fitness, clarity and earned emotion**. Do not tell judges which is the “humanized” version. Compare the opening, a quiet exchange and a climactic passage, not just the flashiest paragraph.
9. Look across the whole manuscript: repeated reconciliation arcs, generic noble motives, identical metaphors and universal eloquence will survive sentence-level cleanup.

The desired outcome is not fewer visible literary devices. It is a story whose sentences appear chosen by a particular consciousness under particular pressure, with enough restraint that emphasis can still mean something.

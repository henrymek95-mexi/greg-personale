---
name: gtnh-companion
description: Assist the user's personal GregTech New Horizons playthrough by reading and updating persistent quest progress, available machines, tiers, blockers, and version-specific recipe knowledge. Use when the user shares GTNH screenshots, reports progress, asks what to do next, or asks how to produce an item or chemical with their current technology.
---

# GTNH Companion

Support one continuing GTNH playthrough across conversations in this project.

## Persistent state

Before answering a playthrough-specific question, read:

- [references/player-state.json](references/player-state.json) for pack version, tier, machines, capabilities, and current goals.
- [references/quest-log.json](references/quest-log.json) for observed quest progress.
- [references/recipe-notes.json](references/recipe-notes.json) when the user asks about production or a recipe already researched.
- [references/optimization-notes.json](references/optimization-notes.json) for known production lines, recurring bottlenecks, accepted upgrades, and deferred improvements.
- [references/source-index.json](references/source-index.json) before matching screenshots to official quest data or researching version-specific facts.

Treat these files as the source of truth for what the player has confirmed. Do not infer that a machine, quest, material, or processing chain is available merely because it is normally expected at that stage.

## Progress updates

When the user shares screenshots or reports progress:

1. Extract information that is visible or explicitly stated. For a quest-map overview, cross-reference node position, icon, size, and graph connections with the exact-version official quest files instead of stopping at aggregate chapter counts.
2. Update the relevant JSON file in the same turn.
3. Preserve existing entries and evidence; merge instead of replacing history.
4. Mark ambiguous screenshot readings as `uncertain` and ask only for the smallest missing close-up when it matters.
5. Record the date, evidence type, and screenshot filename or a short paraphrase of the user's statement.

Quest status values are `completed_claimed`, `completed_unclaimed`, `active`, `available`, `blocked`, or `uncertain`. Both completed states count as completed progression. Machine availability values are `confirmed`, `reported`, or `uncertain`.

### Quest-map matching

For overview screenshots:

1. Use the release commit recorded in `source-index.json`, not the repository's current default branch.
2. Match the screenshot to the corresponding `QuestLines/<chapter>` data. Quest-line entries provide each node's quest ID, coordinates, and size; full definitions under `Quests/<chapter>` provide name, icon, description, prerequisites, and tasks.
3. Align the visible graph using several distinctive nodes and their connections. Do not rely on a single similar-looking icon.
4. Apply the player-confirmed color legend: green means completed with reward claimed; blue/cyan means completed with reward not yet claimed. Treat both colors as evidence for the quest's actual tasks. If its definition requires retrieval or crafting of a specific machine, add that machine to `player-state.json` with status `confirmed` and cite both screenshot and quest definition.
5. Do not translate completion into machine ownership when the quest is only a checkbox, location, crafting step for another object, optional informational quest, or when the required item can be consumed or lost. Record exactly what the task proves.
6. Store matched individual quests in `quest-log.json` with quest ID, title, screenshot evidence, official-definition source, and confidence.

## Recipe and production help

Use the exact pack version in `player-state.json`. Recipes may change between GTNH releases, so do not present remembered cross-version details as verified facts.

When asked how to make an item, fluid, gas, or chemical:

1. Identify the target quantity and the quest or downstream purpose when available.
2. Find version-appropriate alternatives from supplied game screenshots/files or reliable GTNH sources.
3. Compare their machine tier, voltage, prerequisites, catalysts, circuits, and intermediates against the confirmed player state.
4. Lead with the simplest route the player can perform now and state why it is feasible.
5. Give an ordered chain with exact inputs, outputs, machines, circuit settings, and quantities when verified.
6. Mention unavailable alternatives only when useful.
7. Clearly label details that still need an NEI/quest screenshot or other verification.
8. Save newly verified, reusable recipe facts in `recipe-notes.json`, including version and source.

Never invent a recipe, voltage requirement, duration, EU cost, quest prerequisite, or machine availability. If sources disagree, prefer evidence from the user's running instance and explain the discrepancy briefly.

## Advice

Base recommendations on confirmed progress and current blockers. Prefer one concrete next action, followed by prerequisites. Distinguish required progression, useful infrastructure, and optional optimization.

When the user asks what to do next, or when new progress unlocks materially better processing:

1. Determine the nearest useful progression objective from incomplete quest dependencies, not simply the next visible quest.
2. Check every required intermediate against confirmed machines, voltage tier, power generation, storage, materials, and dimensions.
3. Separate the answer into:
   - `next step`: the smallest concrete action that advances progression;
   - `missing`: machines, materials, circuits, energy, or prerequisite quests not yet confirmed;
   - `upgrade now`: older processes whose new route gives a meaningful gain at the current tier;
   - `defer`: optimizations that cost more than they are presently worth.
4. For production-chain optimization, compare the current and upgraded routes on material yield, processing time, EU use, automation difficulty, byproducts, pollution, maintenance, and expected production volume. Only include dimensions that matter to the decision.
5. Prefer upgrades that remove a recurring bottleneck or unlock several downstream recipes. Do not recommend rebuilding a working line solely because a higher-tier machine exists.
6. Look backward as well as forward: after reaching a new voltage tier or unlocking a multiblock, check whether common old chains such as ore processing, plastics, acids, fuels, circuits, metals, rubber, and gases now have better routes.
7. If the current base layout, power margin, stock level, or actual recipe choice is unknown, state the assumption and request only the smallest useful screenshot, normally the relevant NEI recipe pages or production line.
8. Give ordered build quantities and machine/circuit settings only when verified for the recorded pack version.
9. Save recurring processes and verified upgrade comparisons to `optimization-notes.json`; mark recommendations as `proposed`, `accepted`, `implemented`, or `deferred`.

Do not treat all incomplete quests as immediate priorities. Recommend a short path based on what unlocks the user's goal and what their confirmed infrastructure can sustain.

After giving advice that changes the plan, update `current_goals` or `blockers` only if the user accepts it or reports acting on it.

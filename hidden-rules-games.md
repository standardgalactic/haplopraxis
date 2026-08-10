# Games with Hidden or Unknown Rules

## Conventional secret vs unknown law

A conventional game secret is usually a lookup fact: a hidden room, a code, a coordinate, a one-off unlock action.

Haplopraxis treats hiddenness differently:

- The world may behave in ways that are lawful but not yet legible.
- A player can build a working theory that later fails.
- The failure is evidence that the model was incomplete, not that a password was missing.

The target experience is discovery through anomaly, hypothesis, and revision.

## Background: classes of hidden-rule design

Many games already hide rules in useful ways:

1. **Opaque-start puzzle systems** where outcome logic is inferred from repeated trial.
2. **Social deduction systems** where intent and role information are hidden.
3. **Emergent sandboxes** where small public rules yield surprising composites.
4. **Procedural/roguelike loops** where uncertainty renews each run.
5. **Metagame/ARG structures** where rule discovery crosses files, logs, and artifacts.

Haplopraxis borrows from these, but emphasizes historical causality and reconstruction.

## Haplopraxis architecture for unknown-law play

The game now uses a historical rule engine that records interactions and derived consequences as structured lineage history.

Design goals:

- Avoid static "do X to unlock Y" Easter eggs.
- Make causality compositional (predicates over history, not isolated one-off switches).
- Preserve developmental opacity (present state alone is not always enough to explain itself).
- Preserve forensic recoverability via replay/export/lineage inspection.

Implemented mechanism families include:

- **Simple repeat regularities** (inferable from repeated encounters).
- **Ordering-sensitive regularities** (same elements, different sequence, different result).
- **Delayed predicate consequences** with long lags between cause and effect.
- **Lineage-depth/accumulated-state effects** that depend on historical burden.
- **Statistical regularities** that become clearer only across many exported histories.
- **Emergent apparent rules** that are surface effects of deeper interacting factors.
- **Rare singular mutation events** that permanently alter future world behavior.

This document intentionally does **not** disclose concrete trigger predicates or an exploit checklist.

## Forensics and observability

To support scientific-style investigation without full spoiler disclosure, exported lineage data includes:

- Event ordering and turn indices.
- Timestamps and encounter indices.
- Parent/ancestry links between consequences and prior causes.
- Lineage depth and inheritance context.
- State snapshots and transitions.
- Rule-family identifiers (opaque labels, not human-readable solutions).
- Consequence metadata useful for cross-run comparison.

As a result, players can compare many playthroughs with external analysis tools and test hypotheses statistically.

## Why this matters

The intended difficulty is not just steering through the starfield.
It is determining what system is being observed, where:

- laws are discoverable,
- models are falsifiable,
- and historical traces become research material.

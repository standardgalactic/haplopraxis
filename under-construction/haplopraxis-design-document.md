# Haplopraxis — Design Notes

*A tiny web game where history is the world. Private space, shared history.*

Repo: `standardgalactic/haplopraxis` — current build is the "Starfield edition" / Playable Baseline.

---

## Premise

The game begins in the year **2400**. Players navigate a starfield of roughly 150,000 star systems in a ship, using bubble/sphere mechanics derived from Spherepop principles. There is no hidden state — everything that happens is an append-only event history (`POP`, `REFUSE`, `BIND`, `COLLAPSE`, `SEEN`), and the order in which a player encounters things determines what can later be reconstructed about the world ("the order you see things changes the autopsy").

### Framing: history-theoretic, not merely continuation-theoretic
The slogan "history is the world" is not metaphorical. The event log is the ontology; states are derived views over it. The event vocabulary (`POP`, `REFUSE`, `BIND`, `COLLAPSE`, `SEEN`) descends from Spherepop's operational vocabulary, but in the game these stop being language operations and become **world events**. Reconstruction is therefore not a narrative theme layered on top — it is the primary epistemic challenge a player faces. A player arriving after a global reset is literally performing archaeology on their own world.

### Event Ontology
The five primitive event types are not implementation detail — they function as the game's equivalent of physical laws:

- **`POP`** — an outer boundary triggered/burst, forcing outer-scope evaluation (see §Bubble/Sphere Mechanic).
- **`REFUSE`** — a rejected interaction or transformation.
- **`BIND`** — an established relationship or attachment between entities.
- **`COLLAPSE`** — a scope resolving into a final state (e.g. innermost-bubble evaluation completing).
- **`SEEN`** — a detection/observation event (e.g. an inhabitant becoming aware of a player).

> The world consists of histories composed from five primitive event types. All higher-level phenomena are derived from these events.

This gives the event vocabulary the same foundational role in the game that particles and forces play in a physics engine — everything else (bubbles, detection, flares, resets) is a derived pattern built from these five primitives.

### Visual Style
The world is rendered deliberately sparse — outline-only — as the **Level 1** presentation. Objects gradually blur and thicken unless refreshed by movement or blinking, so players never hold perfect information; perception itself has to be continually maintained rather than passively received.

---

## Time System

The eleven-hour watch, the zoom-scaled time system, the desynchronization mechanics, and the time crystals are all pieces of one temporal architecture — not separate features. The planned physical watch (see §Physical tie-in below) is not merchandise attached to the game; it's the first case where a Haplopraxis coordinate system escapes into the real world. It's suited to that role specifically *because* it's the one part of the temporal system stable enough to export — unlike zoom-scaled time, it never needs correction. Manufacturing and fulfillment for the watch would run through [[urfn-ccfa]]'s physical-realization layer as one product line among several — Haplopraxis is a self-contained game design independent of that spec, and doesn't rely on URFN existing or succeeding for its own mechanics to work.

### The Eleven-Hour Clock
- An analogue watch face with **11 hours instead of 12**.
- The choice of eleven is not arbitrary: "Haplopraxis" has eleven letters.
- Two revolutions per day → **22 game hours per real day**.
- Each game hour = 24 ÷ 22 = **1.090909... real hours**.
- Because it's two revolutions (same as a standard 12-hour clock), the watch stays permanently synced to real time — no drift. This is the fixed timekeeping baseline everything else departs from. (Note: the drift-free property comes from doing two revolutions per day, not from the radix being 11 specifically — any n-hour face doing two revolutions per day stays synced, since 24 ÷ 2n is always a clean ratio. Eleven was chosen for the letter-count reason above, not because it's functionally required. This also means the choice genuinely doesn't generalize cleanly: a version of the game built under a different name could reasonably need a different clock radix — e.g. an 18-hour or 210-hour face — which raises the possibility that different named implementations of this concept might need to be genuinely different games rather than reskins of one design.)
- At extreme zoom-in, the effect is visible on the watch itself: the second hand behaves like an hour hand, appearing to nearly stop — an ambient, wordless signal that a player is deep in a slow-time state without needing to check anything in-game.
- Physical watches are planned as a real-world product, synced to game time (see [[urfn-ccfa]] for the broader physical-goods context — currently set aside).
- **Liability/manufacturing note:** the dial needs some clear indication that it runs on non-standard ("long") hours, both to avoid confusing real-world timekeeping and to limit liability exposure. An analogue version is cheap to produce (only the face changes, not the mechanism); a redesign for a digital version is more involved.

### Digital Watch Variant (Advanced Players)
Rather than the standard date, a digital version would display the **in-game year** — a different and arguably more necessary function than the analogue face, since zoom level makes elapsed in-game time wildly non-obvious: zoomed in, years barely move; zoomed out, years fly by. The analogue face answers "what's the fixed real-time baseline"; the digital face answers "what year am I actually at," which the analogue face structurally can't display (an hour hand only has 11–22 positions; in-game years can span millennia).

### Zoom Abandonment Risk
Leaving the game zoomed far out and unattended is a real risk, not just an inconvenience: millions of in-game years can pass while a player is away. Factories or settlements left running during that time may produce unintended results, and in-game civilizations can develop consequences — including self-destructive outcomes — that trace back to a minor decision the player made long before, without the player having any say in what happened while they weren't watching. This is a distinct failure mode from the global reset: the reset is sudden and shared across all players; zoom-abandonment drift is slow, private, and its consequences are entirely the absent player's own history to reconstruct.

### Companion Artifact: The Color-Changing Orb
A planned second physical artifact, distinct from the watch. It functions as a clock via a fixed spectral cycle (color changes over time rather than hands moving), and doubles as a status indicator — its color aura shows when a player's system is under attack (rare) or when the player is near a texture or time crystal. Where the watch is meant to be a stable, drift-free coordinate reference, the orb is deliberately reactive and event-driven — a second channel for information the watch's steady hands aren't suited to carry.

### Zoom-Based Time Scaling
- Zooming **in** slows time down; zooming **out** speeds it up.
- This lets scale and timescale stay aligned in the interface: zoomed out, you can watch galaxies drift; zoomed in, you can watch molecular motion — all through the same zoom control.
- This was a *side effect*, not an original design goal, of tying timescale to zoom level.
- Formally: `t_local = f(z) · t_global`, where `z` is zoom level. This means time stops being a universal coordinate — two players at different zoom levels are not living in the same effective present.
- Precedent: this solves the same practical problem as early JavaScript solar-system visualizers (seen roughly 10–20 years ago) — zoomed out, time had to speed up just to make orbits visible at all; zoomed in on near orbitals, time had to slow down or the motion was too fast to follow. The mechanic isn't purely thematic; it grew out of a real, previously-solved visualization constraint.

### Desync and Correction
- Because zoom changes your effective timescale, it desyncs your position from the "real" present: zooming out moves you further into the future; zooming in delays your plans relative to everyone else.
- **Time crystals** and **texture crystals** correct this desync, letting a player skip time backward or forward to resolve the mismatch. Functionally these are **synchronization devices** — they reconcile a player's local history (`t_local`) with the shared global history (`t_global`) — rather than time-travel devices in the conventional sense.
- Outside of crystal use, players can skip forward one year at a time via a button press, but **cannot ordinarily go backward**.

### Global Reset
- Holding or spamming the **"g" key** too long triggers a **global reset** — the entire universe resets to zero for *all* players.
- Recovery takes **five minutes**, climbing back to the present **logarithmically** (fast at first, slower as it approaches now).
- Everyone loses progress in a reset — **except** players with **autoblink** enabled, who are exempt.
- Functionally, this makes a careless keypress by anyone into a shared historical event the whole player base has to live through and reconstruct around. Unlike most games, where a reset is an administrative event outside the fiction, here it becomes part of history itself — the kind of thing that generates emergent, unscripted folklore ("the reset of June 17th") purely from mechanics rather than authored lore.

### Unresolved: Annual Reset Prototype
One prototype version had the game reset to year 2400 every *real-world* year. This was never fully worked out and raises a genuine, non-minor complication: for a player joining partway through such a cycle, the in-game year would always begin at 2400 for them specifically — meaning new-player onboarding and the shared-history model would need to interact in some way that hasn't been designed yet. Left as an open problem rather than a resolved mechanic.

New players also don't see the full 150,000-name Wikipedia-derived star set immediately — only around 1,000 names, which repeat, until a later unlock reveals the rest. This softens the same onboarding problem in a different dimension: a new player's *spatial* horizon is deliberately narrowed the same way their *temporal* horizon is (always starting at 2400), so both space and time present as smaller, more repetitive, and less "real" until the player has earned expanded access to each.

### Synchrony as a Resource
Most games assume synchrony (a shared present) and make material resources scarce. Haplopraxis inverts this: material resources are relatively abundant (a wide, generous starfield; a minimal three-resource Level 1 economy), but **synchrony is expensive**. Every player inhabits a different effective historical frame the moment they zoom, and time/texture crystals exist specifically to reconcile incompatible chronologies rather than to unlock material wealth. Read this way, the scarce resource the whole time system is organized around isn't matter or energy — it's a shared present.

---

## Detection & Stealth

Most stealth games ask *"have I been seen?"* — a visibility problem. Haplopraxis asks *"did I evaluate the boundary correctly?"* — an **evaluation-order problem**. A careless traversal triggers the outer scope; a careful one preserves access to the inner scope. This is what ties stealth, diplomacy, and computation together as one mechanic rather than three separate systems.

### Blinking
- Ships must **blink** when passing through a bubble or sphere, or they pop it.
- **A then B** activates **autoblink**, which blinks automatically when necessary.
- Most experienced players keep autoblink on most of the time — it mainly functions as a filter separating brand-new players (or very young children) from everyone else, rather than an active skill test for veterans.
- Philosophically: blinking is *correct traversal*; autoblink is *delegated traversal* — the player automates their own adherence to a continuation-preserving rule rather than performing it manually. That raises an open design question worth keeping in mind for future systems: is expertise in this game about knowing when to blink, or about knowing what can safely be automated?

### Two-Phase Detection
- **Outer planetary region:** drones already know your location and actively home in on you — impersonal, always-on surveillance.
- **On the ground, among inhabitants:** passing through a bubble *inappropriately* (i.e. popping it instead of blinking through) is what alerts inhabitants to your presence.
- Planets range from **hostile to very friendly** — but detection is disruptive either way. Friendly inhabitants don't attack, but they will **throng to meet you**, which interrupts whatever you were doing just as surely as a hostile response would.
- Living peacefully among an alien people requires passing through their outer bubble without popping it.

---

## The Bubble/Sphere Mechanic (Spherepop Principles)

- Core rule: the goal is to find and pop the **innermost** bubble, which triggers an evaluation sequence.
- If you pop an **outer** bubble while passing through it, the outer scope evaluates first — and this **automatically sets off the innermost bubble**, destroying your ability to ever reach it deliberately. The boundary is effectively removed by the act of touching it carelessly.
- This is not just flavor — it's a real evaluation-order rule, and it scales across contexts:
  - **Tutorial layer:** used to teach evaluation of ordinary algebraic expressions and simple game mechanics.
  - **Simulator layer:** in factory, city, and planetary simulators, entering a bubble means literally entering that settlement's planetary scope. Careless entry (a "pop") alerts the inhabitants; careful entry (a "blink-through") lets you pass unnoticed.
- One formal principle — innermost-first evaluation, destroyed by outer-scope contact — produces algebra tutorial, stealth mechanic, and diplomatic/first-contact mechanic simultaneously.

---

## Multiplayer / Social Layer

**Effectively single-player, asynchronously multiplayer.** Each player is assigned a kind of hash that places them in a very far-off, unique region of the ~150,000-system space — that distance is what makes moment-to-moment play feel solitary while the world still feels inhabited. What you actually encounter are **local aliens** — technically NPCs, but their parameters are set by whichever player was most recently in that area. Other players shape the world through NPC behavior rather than through direct contact. The global reset (§Global Reset) is the one mechanic that ties everyone together into a single shared moment.

Most MMOs are **shared space, private history** — everyone occupies the same map, but each player's story is their own. Haplopraxis inverts this: **private space, shared history.** Players are physically separated by enormous distances, yet are united through the historical consequences of actions. What connects players isn't location — it's chronology.

Despite the distance, direct player-to-player communication exists: players can interact with each other's planets, send messages, or send **particle packets** from their star bases.

- Player locations are **broadcast** to other players.
- Other players can build **stellar minefields** and **Dyson spheres** around a player's systems in response to that broadcast presence — meaning simply existing somewhere is a strategic exposure, not a neutral fact, even without direct encounters.
- This inverts the usual MMO default, where location is private until discovered. Here, everyone already knows where everyone is; the game is not about scouting, it's about **what other players choose to build around what they already know** — conflict shifts from discovery to interpretation.

---

## World Generation & Persistence

### Knowledge as Geography
Star systems and planets are generated from Wikipedia topics, scientific concepts, and article structure. Early planetary systems correspond to section headings — the topology of knowledge becomes the topology of space. A player wanting to learn about a concept can simply fly there; reading and exploring become the same act.

Most educational games attach facts to places as a layer on top of gameplay. Haplopraxis does something stronger: knowledge *is* the geography, not a decoration applied to it. A player traveling between concepts is literally moving through a graph of human knowledge — the topology of ideas becomes navigable space, and there's no privileged entry point or required order (see §Rhizomatic exploration under Theoretical Resonances). This also means the game's map is never "finished" in the way a hand-authored world is — it's exactly as large and as structured as the source knowledge graph.

### Flares as Distributed Memory
Flares are permanent — a flare never disappears. Over time, players collectively write a visible, persistent history into the universe. Functionally, the flare network behaves like a distributed memory system: structures other players leave behind help future traversals survive.

Given that resets are disasters and flares survive them, flares function less like ordinary game markers and more like **monuments, inscriptions, or road markers** — a civilization-scale memory system built entirely from player action rather than authored content. A flare network a player encounters is not just a gameplay aid; it's evidence of a prior traversal, readable the way an archaeologist reads a trail of artifacts. This is the concrete mechanical form the game's "history is the world" thesis takes at the level of shared space: the flare network *is* the persistent record other players actually leave behind, as opposed to the ephemeral, privately-held traversal history each individual player experiences.

### Resource Economy
Deliberately minimalist and tiered:
- **Level 1:** ironium, boronium, germanium. Visuals are outline-only (see §Visual Style).
- **Level 2:** texture crystals, time crystals. Texture crystals let players add **surface** to objects **temporarily** — the game's outline-only presentation is not a permanent aesthetic limit but a Level 1 condition that texture crystals can locally override. Reaching Level 2 is deliberately difficult: it requires **visiting all 150,000 stars**.

A small primitive vocabulary generating large strategic and narrative consequences — the resource system's counterpart to Spherepop's small operational vocabulary (`POP`, `REFUSE`, `BIND`, `COLLAPSE`) generating large emergent structure.

---

## The Layers of Play

Read as a whole, the design has four layers stacked on top of each other:

0. **Perception — a maintenance game, underneath everything else.** Before a player can navigate at all, they must continually maintain a world model: the outline-only visuals blur and thicken unless refreshed by movement or blinking. Perception is not free; information decays. A player is performing active reconstruction from the first second of play, not just once historiography (layer 3) becomes relevant.
1. **Level 1 — a traversal game.** Players navigate an outline-only universe, gather three basic resources (ironium, boronium, germanium), blink through spheres, and learn the core evaluation-order mechanic.
2. **Level 2 — a synchronization game.** Players acquire texture and time crystals and begin actively managing local vs. global history — correcting desync, temporarily restoring surface detail, working with the `t_local = f(z) · t_global` relationship instead of just experiencing it passively.
3. **Level 3 (implicit, not a spec'd mechanic) — a historiography game.** Players stop merely playing the world and start interpreting it: reconstructing what happened from flares, NPC parameterization, and other players' traces. This layer isn't a separate mode the game switches into — it emerges from layers 0–2 once enough shared history has accumulated. Most games never reach this layer; here it's closer to the point.

---

## Scientific Inspiration & Additional Mechanics

- Draws on **quantum mechanics, autocatalytic sets, complexity theory, and condensed matter physics**.
- Star systems and planets are named after scientific theories and concepts — an educational layer woven into exploration rather than a separate mode.
- Additional mechanics: **firing crystal bubbles**, manipulating a **color wheel**, adjusting **contrast**, and dedicated keys for **boosting acceleration** (alongside blink/autoblink).
- Includes deliberate **comedic and absurdist moments** — the tone isn't purely theoretical/austere.
- **Design influence, not yet adapted:** the 1995–98 4X game *Stars!* (and its strategy guides, in-game manual, and tutorial) is a longstanding reference point — revisited as a kid well after having already mastered the game, specifically for its formal structure rather than its strategies. Two ideas under consideration for adaptation: (1) *Stars!*'s point-buy race-creation system, where racial traits cost or grant points and every tradeoff is explicit and mutually exclusive — a possible template for letting players formally choose their starting relationship to synchrony, stealth, or detection sensitivity, rather than that being purely emergent playstyle; (2) its tunable resource-production formulas (output scaling non-linearly with population, tech level, and adjustable coefficients) — a possible starting point for a production formula for Haplopraxis's own resource tiers, potentially keyed to something like distance-from-shared-present rather than population. Neither has been adopted yet; both are open design directions.

---

---

## Theoretical Resonances

*The following connects Haplopraxis to the broader theoretical corpus (Spherepop, MEM|8, reconstruction/repair/admissibility work). These are readings and interpretive connections, not specified game mechanics — included because they clarify design intent, not because the game encodes them literally.*

**Exact vs. inexact representation.** The event log is exact; any player's understanding of it is inexact. This mirrors the distinction between exact and approximate representations elsewhere in the corpus — the world a player experiences is always a reconstruction, never the thing itself.

**History over state.** The core slogan is not decorative. MEM|8's treatment of memory as event history rather than static storage, Spherepop's emphasis on histories over states, and the reconstruction/repair essays all converge on the same claim Haplopraxis enacts mechanically: state is a derived summary, history is primary.

**Traversal dependence and reconstruction.** A player arriving after a reset performs archaeology. A player encountering another's flare network reconstructs a prior traversal. A player interpreting NPC behavior is reconstructing another player's history indirectly. This is the "autopsy" framing applied at every scale of the game, from a single bubble to the whole shared universe.

**Local time as duration.** The zoom-scaled time system, where different zoom levels inhabit different effective presents, resonates with Bergson's *durée* — time as a property of perspective rather than a shared external coordinate. The `t_local = f(z) · t_global` relationship gives that resonance an actual formal shape rather than leaving it purely metaphorical.

**Rhizomatic exploration.** The Wikipedia-derived star topology has no privileged root — a player can begin almost anywhere and wander indefinitely through a network rather than climbing a hierarchy. This resembles Deleuze's rhizome more than a conventional tech-tree or curriculum structure.

**Persistence through maintenance.** Flares, civilizations, routes, and settlements persist not because they exist statically but because players keep reconstructing and revisiting them — closer to Prigogine's dissipative structures (order maintained through continuous throughput) than to a save-file model of permanence. This is the same idea behind "operator ecology" elsewhere in the corpus: what survives is what keeps getting used, not what was merely built once.

**Observation as intervention.** The pop/blink distinction — passing through a boundary correctly preserves structure, incorrectly destroys it — mirrors the broader theme that continuation depends on *how* something is traversed, not merely on what it is. Observation has a cost; it is never neutral.

**Approximate probabilistic simulation as cognition (direct design inspiration).** Battaglia, Hamrick & Tenenbaum's 2013 PNAS paper "Simulation as an engine of physical scene understanding" was a direct inspiration, not just a resonance. The paper argues human physical reasoning runs on an "intuitive physics engine" (IPE) — approximate, probabilistic mental simulation — rather than rules-of-thumb or symbolic computation, and this maps closely onto the game's own mechanics:
- *Simulation over symbolic computation:* the IPE predicts by running forward physics rather than solving equations, the same way Haplopraxis reconstructs the world through traversal and event history rather than querying a static "true" state.
- *Probabilistic, not deterministic:* the paper's central finding is that people match reality *worse* when given exact coordinates and match human judgment *better* when given realistically approximate ones. This is close to the literal mechanics of the outline-only/blur-then-refresh visual model — imprecision isn't a limitation added on top of perception, it's what makes reconstruction feel psychologically right.
- *Few samples, not exhaustive computation:* the paper finds human judgments are consistent with only 3–7 mental simulation runs rather than an exhaustive posterior — a real empirical anchor for why the zoom-scaled, always-decaying perception model is plausible as a *cognitive* model, not just a thematic one.
- The paper's correlation numbers (ρ=0.92 for the probabilistic model vs. ρ=0.64 for ground truth against human judgment) are effectively an empirical argument, in a different domain (physical scene stability), for the game's core thesis — that history/approximation is more fundamental to lived understanding than ground-truth state.

**One-sentence summary (external framing):** *Haplopraxis is a massively distributed archaeology game disguised as a space exploration game.* An alternate framing that emphasizes the private-space/shared-history structure more directly: *Haplopraxis is a game where history is the only shared map.*
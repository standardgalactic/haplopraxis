import os, textwrap, json, zipfile, pathlib, time
from pathlib import Path

base = Path.cwd()

os.makedirs(base, exist_ok=True)

# Files content
index_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Haplopraxis</title>
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <main id="screen" class="screen" aria-live="polite"></main>
  <script src="./game.js"></script>
</body>
</html>
"""

styles_css = """/* Haplopraxis — minimal CRT */
:root{
  --bg:#0b0e0c;
  --fg:#b6ffb6;
  --accent:#22ff66;
  --dim:rgba(182,255,182,0.70);
  --shadow:rgba(0,255,100,0.20);
}
*{box-sizing:border-box}
body{
  margin:0;
  padding:2rem;
  background:var(--bg);
  color:var(--fg);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
.screen{
  max-width: 760px;
  margin: 0 auto;
  border: 1px solid var(--accent);
  padding: 1.5rem;
  box-shadow: 0 0 22px var(--shadow);
}
.gameTitle{
  text-align:center;
  margin-bottom:1.5rem;
}
.gameTitle .name{
  font-size:1.5rem;
  letter-spacing:0.02em;
}
.gameTitle .tag{
  font-size:0.85rem;
  opacity:0.75;
}
.headerbar{
  display:flex;
  gap:0.75rem;
  flex-wrap:wrap;
  align-items:center;
  justify-content:space-between;
  margin-bottom: 1rem;
}
.headerbar .left{
  opacity:0.95;
}
.headerbar .right{
  display:flex;
  gap:0.5rem;
  flex-wrap:wrap;
}
button{
  background: transparent;
  color: var(--fg);
  border: 1px solid var(--accent);
  padding: 0.35rem 0.6rem;
  cursor:pointer;
}
button:hover{ background: rgba(0,255,100,0.10); }
.nodeTitle{
  font-size:1.15rem;
  margin-top: 1.25rem;
  margin-bottom: 0.6rem;
}
.text{
  white-space:pre-wrap;
  margin-bottom: 0.9rem;
  opacity:0.95;
}
.item{
  border: 1px dashed var(--accent);
  padding: 0.55rem;
  margin: 0 0 0.55rem 0;
  cursor: pointer;
  opacity:0.92;
}
.item:hover{ background: rgba(0,255,100,0.07); }
.actions button{
  display:block;
  width:100%;
  text-align:left;
  margin-bottom:0.5rem;
  padding:0.6rem;
}
.log{
  margin-top: 1.6rem;
  font-size: 0.85rem;
  opacity:0.65;
}
.smallNote{
  font-size:0.85rem;
  color: var(--dim);
}
"""

game_js = r"""/* Haplopraxis — event-historical prototype (GitHub Pages friendly) */

/* ============================
   EVENT HISTORY
============================ */

let history = [];
let foreignLineage = false;

/** Utility: does history contain this exact label? */
function has(label) {
  return history.some(e => e.label === label);
}

/** Seen traces: items remember being encountered (rendered) */
function seen(itemId) {
  return history.some(e => e.label === `seen:${itemId}`);
}
function see(itemId) {
  if (!seen(itemId)) {
    history.push({ type: "SEEN", label: `seen:${itemId}`, t: Date.now() });
  }
}

/** Compare encounter order of two items */
function sawFirst(a, b) {
  const ta = history.find(e => e.label === `seen:${a}`)?.t;
  const tb = history.find(e => e.label === `seen:${b}`)?.t;
  if (!ta || !tb) return null;
  return ta < tb ? a : b;
}

/** Add an event (blocked in archaeological mode) */
function addEvent(type, label) {
  if (foreignLineage) return; // archaeology, not intervention
  history.push({ type, label, t: Date.now() });
  processDelayed();
  render();
}

/* ============================
   IMPORT / EXPORT
============================ */

function exportHistory() {
  prompt("Copy your lineage (JSON):", JSON.stringify(history));
}

function importHistory() {
  const raw = prompt("Paste a lineage to excavate (JSON):");
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new Error("Not an array");
    history = parsed;
    foreignLineage = true;
    // Imported lineages may not have delayed queues; that's fine because autopsy is derived from history.
    // Also ensure that "seen:" traces exist only if present in lineage; we do not auto-add in archaeology mode.
    render();
  } catch {
    alert("Invalid lineage.");
  }
}

function resetRun() {
  // hard reset back into playable mode
  history = [];
  foreignLineage = false;
  delayed.length = 0;
  render();
}

/* ============================
   DELAYED CONSEQUENCES
============================ */

/*
Delayed effects are not timers.
They are predicates over history.
When their trigger becomes true,
they fire exactly once.
Some are persistent (cannot be escaped by collapse).
*/
const delayed = [];

function scheduleDelayed({ trigger, effect, persistent = false }) {
  delayed.push({ trigger, effect, persistent, fired: false });
}

function processDelayed() {
  delayed.forEach(d => {
    if (!d.fired && d.trigger(history)) {
      d.fired = true;
      d.effect();
    }
  });
}

/* ============================
   POSSIBILITY ACCOUNTING
============================ */

/** Count still-admissible actions across visible nodes */
function possibleActions() {
  if (exhausted()) return 0;
  let count = 0;
  Object.values(nodes).forEach(node => {
    if (!node.visibleIf()) return;
    // item clicks are "actions" in the sense of admissible events
    if (node.items) {
      node.items.forEach(i => {
        if ((!i.visibleIf || i.visibleIf()) && (!foreignLineage)) count++;
        // In archaeology mode we treat affordances as inert, so they don't count.
      });
    }
    if (node.actions) {
      node.actions.forEach(a => {
        if ((!a.visibleIf || a.visibleIf()) && (!foreignLineage)) count++;
      });
    }
  });
  return count;
}

/** World exhaustion: nothing further admissible */
function exhausted() {
  // We compute exhaustion by: not in archaeology mode, and no visible items/actions exist.
  // If in archaeology mode, autopsy can still be shown if the imported lineage ended (no affordances were taken).
  // For simplicity: autopsy triggers if there are no actionable affordances OR if an explicit marker exists.
  if (has("autopsy")) return true;
  // In archaeology mode, treat as exhausted if the lineage contains any terminal failure marker.
  if (foreignLineage && (has("overexpansion-failure") || has("containment-failure") || has("structural-instability"))) {
    // not strictly exhaustion, but enough to read an autopsy in practice
    return true;
  }
  // Otherwise, compute based on affordances available now
  let any = false;
  Object.values(nodes).forEach(node => {
    if (!node.visibleIf()) return;
    if (node.items) {
      node.items.forEach(i => {
        if ((!i.visibleIf || i.visibleIf()) && !foreignLineage) any = true;
      });
    }
    if (node.actions) {
      node.actions.forEach(a => {
        if ((!a.visibleIf || a.visibleIf()) && !foreignLineage) any = true;
      });
    }
  });
  return !any;
}

/* ============================
   INTERPRETIVE REGIMES (helpers)
============================ */

function before(label) { return !has(label); }
function after(label)  { return  has(label); }
function between(a, b) { return has(a) && !has(b); }

/* ============================
   WORLD DEFINITION
============================ */

const nodes = {
  atrium: {
    title: "The Atrium",
    visibleIf: () => true,
    text: () =>
`The atrium contains several inert structures.
They do not invite action.
They merely permit it.`,

    items: [
      {
        id: "core-conduit",
        label: () =>
          seen("core-conduit")
            ? "The conduit hums faintly. It has been noticed."
            : "A sealed core conduit embedded in the floor",
        visibleIf: () => !has("activate-core") && !has("refuse-core"),
        onClick: () => addEvent("POP", "activate-core")
      },
      {
        id: "warning-inscription",
        label: () =>
          seen("warning-inscription")
            ? "The inscription feels less like advice and more like law."
            : "A warning inscription, partially eroded",
        visibleIf: () => !has("activate-core") && !has("refuse-core"),
        onClick: () => addEvent("REFUSE", "refuse-core")
      }
    ],
    actions: []
  },

  chamber: {
    title: "Inner Chamber",
    visibleIf: () =>
      has("activate-core") &&
      !has("chamber-collapsed") &&
      !has("chamber-entropy-failure"),
    text: () =>
`Power clarifies.
Clarity eliminates futures.
Some consequences arrive late.`,

    items: [
      {
        id: "binding-sigil",
        label: () => {
          if (before("chamber-bound")) return "A sigil etched into the chamber wall.";
          if (between("chamber-bound", "structural-instability")) return "The sigil appears to anchor the chamber.";
          return "The sigil’s meaning no longer matches reality.";
        },
        visibleIf: () => !has("chamber-bound"),
        onClick: () => {
          addEvent("BIND", "chamber-bound");

          // Local delayed collapse (fate after enough POPs)
          scheduleDelayed({
            trigger: h => h.filter(e => e.type === "POP").length >= 3,
            effect: () => addEvent("COLLAPSE", "chamber-entropy-failure"),
            persistent: false
          });

          // Persistent obligation: later refusals awaken structural instability
          scheduleDelayed({
            trigger: h => h.filter(e => e.type === "REFUSE").length >= 2,
            effect: () => addEvent("POP", "structural-instability"),
            persistent: true
          });
        }
      },

      // Conflicting witnesses: order creates epistemic lens
      {
        id: "wall-relief",
        label: () => {
          const first = sawFirst("wall-relief", "floor-diagram");
          if (!first) return "A carved relief depicting energy flowing outward.";
          if (first === "wall-relief") return "The relief confirms that expansion stabilizes the structure.";
          return "The relief appears symbolic, not instructional.";
        },
        visibleIf: () => true,
        onClick: () => addEvent("POP", "relief-interpreted")
      },
      {
        id: "floor-diagram",
        label: () => {
          const first = sawFirst("wall-relief", "floor-diagram");
          if (!first) return "A geometric diagram etched into the floor.";
          if (first === "floor-diagram") return "The diagram indicates containment prevents collapse.";
          return "The diagram appears decorative rather than functional.";
        },
        visibleIf: () => true,
        onClick: () => addEvent("POP", "diagram-interpreted")
      },

      // A "lying" dial: becomes dangerous late
      {
        id: "resonance-dial",
        label: () => {
          if (before("chamber-bound")) return "A resonance dial marked with unfamiliar symbols.";
          if (between("chamber-bound", "structural-instability")) return "The dial appears to stabilize the chamber.";
          return "The dial is miscalibrated. Its markings are obsolete.";
        },
        visibleIf: () => true,
        onClick: () => {
          addEvent("POP", "dial-turned");

          scheduleDelayed({
            trigger: h => has("dial-turned") && has("structural-instability"),
            effect: () => addEvent("POP", "resonance-failure"),
            persistent: true
          });
        }
      }
    ],

    actions: [
      {
        label: "Collapse the chamber and withdraw",
        do: () => addEvent("COLLAPSE", "chamber-collapsed"),
        visibleIf: () => true
      }
    ]
  },

  archive: {
    title: "Silent Archive",
    visibleIf: () => has("refuse-core") && !has("archive-collapsed"),
    text: () =>
`Restraint reveals what power obscures.
The archive is fragile.`,

    items: [
      {
        id: "fragile-tablet",
        label: () =>
          seen("fragile-tablet")
            ? "The tablet’s surface has begun to decay."
            : "A fragile tablet rests on a stone pedestal",
        visibleIf: () => !has("archive-sealed") && !has("tablet-disintegrated"),
        onClick: () => addEvent("POP", "tablet-read")
      },
      {
        id: "empty-pedestal",
        label: () =>
          has("archive-sealed")
            ? "An empty pedestal."
            : "A pedestal that once held something important.",
        visibleIf: () => true,
        onClick: () => addEvent("SEEN", "pedestal-noted")
      }
    ],

    actions: [
      {
        label: "Seal the archive permanently",
        do: () => addEvent("POP", "archive-sealed"),
        visibleIf: () => !has("archive-sealed")
      },
      {
        label: "Collapse the archive into silence",
        do: () => addEvent("COLLAPSE", "archive-collapsed"),
        visibleIf: () => !has("archive-collapsed")
      }
    ]
  },

  instability: {
    title: "Structural Instability",
    visibleIf: () => has("structural-instability"),
    text: () =>
`The structure no longer forgets.
Actions propagate further than intended.
Future collapses will cost more.`,
    items: [
      {
        id: "fractured-inscription",
        label: () =>
          (has("overexpansion-failure") || has("containment-failure"))
            ? "The inscription no longer distinguishes cause from interpretation."
            : "A fractured inscription whose meaning is unclear.",
        visibleIf: () => true,
        onClick: () => addEvent("SEEN", "inscription-noted")
      }
    ],
    actions: [
      {
        label: "Stabilize by sacrificing future possibility",
        do: () => addEvent("POP", "stability-sacrifice"),
        visibleIf: () => !has("stability-sacrifice")
      }
    ]
  },

  autopsy: {
    title: "Autopsy",
    visibleIf: () => exhausted(),
    text: () => generateAutopsy(),
    items: [],
    actions: []
  }
};

/* Schedule the conflicting witness failures (persistent, fate via history) */
scheduleDelayed({
  trigger: h =>
    has("relief-interpreted") &&
    sawFirst("wall-relief", "floor-diagram") === "wall-relief" &&
    h.filter(e => e.type === "POP").length >= 4,
  effect: () => addEvent("POP", "overexpansion-failure"),
  persistent: true
});

scheduleDelayed({
  trigger: h =>
    has("diagram-interpreted") &&
    sawFirst("wall-relief", "floor-diagram") === "floor-diagram" &&
    h.filter(e => e.type === "POP").length >= 4,
  effect: () => addEvent("POP", "containment-failure"),
  persistent: true
});

/* Neglect: tablet can disintegrate if never seen after some history */
scheduleDelayed({
  trigger: h =>
    has("refuse-core") &&
    !seen("fragile-tablet") &&
    h.length >= 6 &&
    !has("tablet-read") &&
    !has("tablet-disintegrated"),
  effect: () => addEvent("POP", "tablet-disintegrated"),
  persistent: false
});

/* ============================
   AUTOPSY (ending as forensic report)
============================ */

function generateAutopsy() {
  const beliefs = [];

  const wFirst = sawFirst("wall-relief", "floor-diagram");
  if (has("relief-interpreted") && wFirst === "wall-relief") {
    beliefs.push("You believed expansion stabilized the structure.");
  }
  if (has("diagram-interpreted") && wFirst === "floor-diagram") {
    beliefs.push("You believed containment prevented collapse.");
  }

  if (has("chamber-bound")) beliefs.push("You believed presence could substitute for understanding.");
  if (has("refuse-core")) beliefs.push("You believed restraint revealed deeper truth.");
  if (has("activate-core")) beliefs.push("You believed power clarified meaning.");
  if (has("structural-instability")) beliefs.push("You accepted instability as a cost of commitment.");
  if (has("tablet-disintegrated")) beliefs.push("You treated neglect as neutral. The world disagreed.");

  if (beliefs.length === 0) beliefs.push("You avoided belief long enough for the world to end anyway.");

  const perspective = foreignLineage
    ? "This world was not enacted by you.\nYou are reading it as evidence.\n\n"
    : "";

  const fingerprint = history.map(e => (e.label || "").slice(0,1)).join("").slice(0, 18);

  return (
`${perspective}The structure is inert.
No further commitments are possible.

This record does not describe the world.
It describes the assumptions under which the agent acted.

` +
beliefs.map(b => "• " + b).join("\n") +
`

The failures that occurred were consistent with these beliefs.
The beliefs were consistent with the order in which evidence was encountered.

Nothing here was random.
Nothing here was inevitable.
Nothing here can be undone.

Lineage fingerprint: ${fingerprint}

This record may be shared.
It is not a solution.
It is a position.` +
(foreignLineage
  ? `

If you had arrived first,
this world would not be the same.`
  : "")
  );
}

/* ============================
   RENDERING
============================ */

function el(tag, cls, txt) {
  const d = document.createElement(tag);
  if (cls) d.className = cls;
  if (txt !== undefined) d.textContent = txt;
  return d;
}

function render() {
  const screen = document.getElementById("screen");
  screen.innerHTML = "";

  // Title
  const title = el("div", "gameTitle");
  title.innerHTML = `
    <div class="name">Haplopraxis</div>
    <div class="tag">a game of irreversible action</div>
  `;
  screen.appendChild(title);

  // Header bar
  const bar = el("div", "headerbar");
  const left = el("div", "left");
  left.innerHTML = `<strong>Possibility Horizon:</strong> ${possibleActions()}`
    + (foreignLineage ? ` <span class="smallNote">— archaeological record</span>` : "");
  const right = el("div", "right");

  const bExport = el("button", null, "Export");
  bExport.onclick = exportHistory;
  const bImport = el("button", null, "Import");
  bImport.onclick = importHistory;
  const bReset = el("button", null, foreignLineage ? "New Run" : "Reset");
  bReset.onclick = resetRun;

  right.appendChild(bExport);
  right.appendChild(bImport);
  right.appendChild(bReset);

  bar.appendChild(left);
  bar.appendChild(right);
  screen.appendChild(bar);

  // Render visible nodes
  const visible = Object.values(nodes).filter(n => n.visibleIf());
  visible.forEach(node => {
    const nt = el("div", "nodeTitle", node.title);
    const tx = el("div", "text", node.text());

    screen.appendChild(nt);
    screen.appendChild(tx);

    // Items (affordances)
    if (node.items && node.items.length) {
      node.items
        .filter(i => !i.visibleIf || i.visibleIf())
        .forEach(item => {
          // In play mode, seeing is a trace; in archaeology mode, do not mutate imported record.
          if (!foreignLineage) see(item.id);

          const it = el("div", "item");
          const labelText = (typeof item.label === "function") ? item.label() : item.label;
          it.textContent = labelText;

          // In archaeology mode, items are inert
          if (!foreignLineage) it.onclick = item.onClick;
          else it.style.cursor = "default";

          screen.appendChild(it);
        });
    }

    // Actions
    if (node.actions && node.actions.length) {
      const acts = el("div", "actions");
      node.actions
        .filter(a => !a.visibleIf || a.visibleIf())
        .forEach(a => {
          const btn = el("button", null, a.label);
          if (!foreignLineage) btn.onclick = a.do;
          else { btn.disabled = true; btn.style.opacity = "0.5"; btn.style.cursor = "not-allowed"; }
          acts.appendChild(btn);
        });
      screen.appendChild(acts);
    }
  });

  // History log
  const log = el("div", "log");
  log.textContent =
    "History: " + history.map(e => `${e.type}(${e.label})`).join(" → ");
  screen.appendChild(log);
}

render();
"""

readme_md = """# Haplopraxis

A tiny web game where **history is the world**.

There is no state machine to “solve.”
There is only an event lineage that permanently narrows the future.

## Run locally

Open `index.html` in a browser.

## Deploy to GitHub Pages

1. Create a new GitHub repo.
2. Add these files to the repo root.
3. Repo → **Settings → Pages** → Deploy from `main` / root.
4. Open the provided Pages URL.

## Share worlds

Use **Export** to copy your lineage (JSON).
Send it to a friend.
They can **Import** to excavate your world as an archaeological record.

Imported worlds are **read-only**: archaeology, not intervention.

## Files

- `index.html` — main page
- `styles.css` — CRT styling
- `game.js` — the game engine (event sourcing)
- `sample-lineage.json` — a small example lineage you can import
"""

sample_lineage = [
  {"type":"SEEN","label":"seen:core-conduit","t":1734980000000},
  {"type":"POP","label":"activate-core","t":1734980000500},
  {"type":"SEEN","label":"seen:binding-sigil","t":1734980000600},
  {"type":"BIND","label":"chamber-bound","t":1734980000700},
  {"type":"SEEN","label":"seen:wall-relief","t":1734980000800},
  {"type":"POP","label":"relief-interpreted","t":1734980000900},
  {"type":"SEEN","label":"seen:floor-diagram","t":1734980001000},
  {"type":"POP","label":"diagram-interpreted","t":1734980001100},
  {"type":"POP","label":"dial-turned","t":1734980001200},
  {"type":"POP","label":"structural-instability","t":1734980001300},
  {"type":"POP","label":"overexpansion-failure","t":1734980001400}
]

files = {
    "index.html": index_html,
    "styles.css": styles_css,
    "game.js": game_js,
    "README.md": readme_md,
    "sample-lineage.json": json.dumps(sample_lineage, indent=2)
}

for name, content in files.items():
    with open(os.path.join(base, name), "w", encoding="utf-8") as f:
        f.write(content)

# Zip it
zip_path = "haplopraxis_github_pages.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for name in files.keys():
        z.write(os.path.join(base, name), arcname=f"haplopraxis/{name}")

zip_path, sorted(os.listdir(base))[:10], os.path.getsize(zip_path)

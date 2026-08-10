// Haplopraxis — starfield runtime with historically generated hidden regularities

const canvas = document.getElementById("starfield");
const context = canvas.getContext("2d");
const HiddenRules = window.HiddenRulesEngine;

const SAVE_KEY = "haplopraxis:save:v2";
const AUTO_SAVE_EVERY_INTERACTIONS = 4;

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

const ui = {
  screen: document.getElementById("screen"),
  sceneText: document.getElementById("sceneText"),
  controlPanel: document.getElementById("controlPanel"),
  lineageLog: document.getElementById("lineageLog"),
  hud: document.getElementById("hud"),
  controlsButton: document.getElementById("toggleControls"),
  saveButton: document.getElementById("saveState"),
  loadButton: document.getElementById("loadState"),
  exportButton: document.getElementById("exportLineage"),
  importButton: document.getElementById("importLineage"),
  replayButton: document.getElementById("replayLineage"),
  forkButton: document.getElementById("forkLineage"),
  importFile: document.getElementById("importFile"),
  easterEggPanel: document.getElementById("easterEggPanel"),
  closeEasterEgg: document.getElementById("closeEasterEgg")
};

let engine = loadEngineFromStorage();
let controlPanelTimeout;
let sceneTimer;

const ship = {
  x: canvas.width / 2,
  y: canvas.height / 2,
  speed: 0,
  maxSpeed: 5,
  accel: 0.1
};

const controls = {
  up: false,
  down: false,
  left: false,
  right: false,
  showLabels: true
};

const planetsList = [
  "Erebus", "Cairn", "Halide", "Nyx", "Orris",
  "Mim", "Vela", "Orbus", "Kestra", "Lumen",
  "Rift", "Talon", "Aster", "Vale", "Odin"
];

const bubbles = [];
const TOTAL_BUBBLES = 600;

for (let i = 0; i < TOTAL_BUBBLES; i++) {
  bubbles.push({
    x: Math.random() * canvas.width - ship.x,
    y: Math.random() * canvas.height - ship.y,
    z: Math.random() * canvas.width,
    size: 3,
    word: planetsList[Math.floor(Math.random() * planetsList.length)],
    isFocused: false
  });
}

let focusedBubble = null;

function loadEngineFromStorage() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) return new HiddenRules.Engine();
    const parsed = JSON.parse(raw);
    return HiddenRules.Engine.fromSave(parsed);
  } catch {
    return new HiddenRules.Engine();
  }

  function normalizeImportPayload(parsed) {
    if (Array.isArray(parsed)) return parsed;
    if (!parsed || typeof parsed !== "object") return null;

    if (parsed.version && parsed.history && parsed.actions) {
      return parsed;
    }

    if (parsed.lineage && parsed.stateSnapshot && parsed.events) {
      return {
        version: parsed.version ?? 2,
        seed: parsed.lineage.seed,
        lineageId: parsed.lineage.id,
        lineageDepth: parsed.lineage.depth ?? 0,
        turn: parsed.stateSnapshot.turn ?? 0,
        encounterIndex: parsed.stateSnapshot.encounterIndex ?? 0,
        worldFlags: parsed.stateSnapshot.worldFlags || {},
        latent: parsed.stateSnapshot.latent || {},
        counters: parsed.stateSnapshot.counters || {},
        memory: {
          wordCounts: {},
          categoryTrail: [],
          interactionTrail: [],
          ancestryAnchors: []
        },
        history: parsed.events,
        actions: parsed.actions || []
      };
    }

    return parsed;
  }
}

function saveEngineToStorage() {
  localStorage.setItem(SAVE_KEY, JSON.stringify(engine.serialize()));
  addLog("State saved.");
}

function showScene(text, ms = 1500) {
  if (!ui.sceneText || !ui.screen) return;
  ui.sceneText.textContent = text;
  ui.screen.classList.remove("hidden");
  if (sceneTimer) clearTimeout(sceneTimer);
  sceneTimer = setTimeout(() => {
    ui.screen.classList.add("hidden");
  }, ms);
}

function addLog(text) {
  if (!ui.lineageLog) return;
  const lines = ui.lineageLog.textContent ? ui.lineageLog.textContent.split("\n") : [];
  lines.push(text);
  ui.lineageLog.textContent = lines.slice(-8).join("\n");
}

function updateHud() {
  if (!ui.hud) return;
  const snapshot = engine.getPublicSnapshot();
  const singularity = snapshot.worldFlags.singularityTriggered ? "yes" : "no";
  ui.hud.textContent =
    `turn=${snapshot.turn} depth=${snapshot.lineageDepth} delayed=${snapshot.counters.delayedTriggered}/${snapshot.counters.delayedExpired} singularity=${singularity}`;
}

function openEasterEggPanel() {
  if (!ui.easterEggPanel) return;
  ui.easterEggPanel.classList.remove("hidden");
  ui.easterEggPanel.setAttribute("aria-hidden", "false");
}

function closeEasterEggPanel() {
  if (!ui.easterEggPanel) return;
  ui.easterEggPanel.classList.add("hidden");
  ui.easterEggPanel.setAttribute("aria-hidden", "true");
}

function toggleControlPanel() {
  if (!ui.controlPanel) return;
  if (ui.controlPanel.style.display === "none") {
    ui.controlPanel.style.display = "block";
    clearTimeout(controlPanelTimeout);
    controlPanelTimeout = setTimeout(() => {
      ui.controlPanel.style.display = "none";
    }, 10000);
    return;
  }
  ui.controlPanel.style.display = "none";
  clearTimeout(controlPanelTimeout);
}

function handleInteraction() {
  if (!focusedBubble) return;
  const result = engine.interact(focusedBubble.word);
  const noteworthy = result.events.filter((e) => e.kind !== "ACTION");

  if (noteworthy.length === 0) {
    showScene(`Interaction recorded at ${focusedBubble.word}.`);
  } else {
    const latest = noteworthy[noteworthy.length - 1];
    showScene(`Anomaly: ${latest.label} (${latest.type})`);
    addLog(`${latest.turn}: ${latest.label} [${latest.ruleFamilyId || "untyped"}]`);
  }

  if (noteworthy.some((e) => e.kind === "ANOMALY_HINT" || e.kind === "HISTORICAL_SINGULARITY")) {
    openEasterEggPanel();
  }

  if (engine.state.counters.totalInteractions % AUTO_SAVE_EVERY_INTERACTIONS === 0) {
    localStorage.setItem(SAVE_KEY, JSON.stringify(engine.serialize()));
  }

  updateHud();
}

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

document.addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase();
  if (ui.screen) ui.screen.classList.add("hidden");

  switch (key) {
    case "c": toggleControlPanel(); break;
    case "w": controls.up = true; break;
    case "s": controls.down = true; break;
    case "a": controls.left = true; break;
    case "d": controls.right = true; break;
    case "x": controls.showLabels = !controls.showLabels; break;
    case "escape": closeEasterEggPanel(); break;
    case " ":
      handleInteraction();
      break;
  }
});

document.addEventListener("keyup", (e) => {
  switch (e.key.toLowerCase()) {
    case "w": controls.up = false; break;
    case "s": controls.down = false; break;
    case "a": controls.left = false; break;
    case "d": controls.right = false; break;
  }
});

ui.controlsButton?.addEventListener("click", toggleControlPanel);
ui.saveButton?.addEventListener("click", saveEngineToStorage);
ui.loadButton?.addEventListener("click", () => {
  engine = loadEngineFromStorage();
  addLog("State loaded.");
  updateHud();
});
ui.exportButton?.addEventListener("click", () => {
  const exportPayload = engine.exportLineage();
  downloadJson(`haplopraxis-lineage-${Date.now()}.json`, exportPayload);
  addLog("Lineage exported.");
});
ui.importButton?.addEventListener("click", () => ui.importFile?.click());
ui.importFile?.addEventListener("change", async (event) => {
  const [file] = event.target.files || [];
  if (!file) return;
  const text = await file.text();
  const parsed = JSON.parse(text);
  const payload = normalizeImportPayload(parsed);
  if (!payload) return;
  engine = HiddenRules.Engine.fromSave(payload);
  addLog("Lineage imported.");
  updateHud();
});
ui.replayButton?.addEventListener("click", () => {
  const snapshot = engine.serialize();
  const replayEngine = HiddenRules.Engine.fromSave({
    seed: snapshot.seed,
    lineageDepth: snapshot.lineageDepth
  });
  for (const action of snapshot.actions) {
    if (action.action === "INTERACT") replayEngine.interact(action.word);
  }
  const same = replayEngine.replaySignature() === engine.replaySignature();
  addLog(same ? "Replay signature matched." : "Replay signature diverged.");
  showScene(same ? "Replay confirmed." : "Replay divergence detected.");
});
ui.forkButton?.addEventListener("click", () => {
  engine = engine.createChildLineage();
  addLog(`Forked lineage depth=${engine.state.lineageDepth}.`);
  updateHud();
});
ui.closeEasterEgg?.addEventListener("click", closeEasterEggPanel);

function update() {
  if (controls.up) ship.speed = Math.min(ship.maxSpeed, ship.speed + ship.accel);
  if (controls.down) ship.speed = Math.max(0, ship.speed - ship.accel);

  for (const b of bubbles) {
    b.z -= ship.speed;
    if (controls.left) b.x += 3;
    if (controls.right) b.x -= 3;
    if (b.z < 1) {
      b.z = canvas.width;
      b.x = Math.random() * canvas.width - ship.x;
      b.y = Math.random() * canvas.height - ship.y;
      b.isFocused = false;
    }
  }

  focusedBubble = null;
  for (const b of bubbles) {
    const scale = canvas.width / b.z;
    const x = ship.x + b.x * scale;
    const y = ship.y + b.y * scale;
    const focused = Math.abs(x - canvas.width / 2) < 20 && Math.abs(y - canvas.height / 2) < 20;
    b.isFocused = focused;
    if (focused && !focusedBubble) focusedBubble = b;
  }
}

function draw() {
  context.fillStyle = "#000";
  context.fillRect(0, 0, canvas.width, canvas.height);

  for (const b of bubbles) {
    const scale = canvas.width / b.z;
    const x = ship.x + b.x * scale;
    const y = ship.y + b.y * scale;

    context.beginPath();
    context.arc(x, y, b.size * scale, 0, Math.PI * 2);
    context.strokeStyle = "#fff";
    context.stroke();

    if (b.isFocused && controls.showLabels) {
      context.fillStyle = "#22ff66";
      context.fillText(b.word, x + 6, y);
    }
  }

  context.strokeStyle = "rgba(34,255,102,0.3)";
  context.beginPath();
  context.arc(canvas.width / 2, canvas.height / 2, 20, 0, Math.PI * 2);
  context.stroke();
}

function loop() {
  update();
  draw();
  requestAnimationFrame(loop);
}

updateHud();
addLog("Historical rules engine active.");
loop();

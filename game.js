// Haplopraxis — minimal, stable baseline
// Starfield + focus + irreversible scene updates

/* =========================
   CANVAS BOOTSTRAP
========================= */

const canvas = document.getElementById("starfield");
const context = canvas.getContext("2d");

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

/* =========================
   CONTROL PANEL
========================= */

let controlPanelTimeout;
const EASTER_EGG_SEQUENCE = "hidden";
let easterEggBuffer = "";

function toggleControlPanel() {
  const cp = document.getElementById("controlPanel");
  if (!cp) return;

  if (cp.style.display === "none") {
    cp.style.display = "block";
    resetControlPanelTimeout();
  } else {
    cp.style.display = "none";
    clearTimeout(controlPanelTimeout);
  }
}

function resetControlPanelTimeout() {
  clearTimeout(controlPanelTimeout);
  controlPanelTimeout = setTimeout(() => {
    const cp = document.getElementById("controlPanel");
    if (cp) cp.style.display = "none";
  }, 10000);
}

function openEasterEggPanel() {
  const panel = document.getElementById("easterEggPanel");
  if (!panel) return;
  panel.classList.remove("hidden");
  panel.setAttribute("aria-hidden", "false");
}

function closeEasterEggPanel() {
  const panel = document.getElementById("easterEggPanel");
  if (!panel) return;
  panel.classList.add("hidden");
  panel.setAttribute("aria-hidden", "true");
}

/* =========================
   SHIP
========================= */

const ship = {
  x: canvas.width / 2,
  y: canvas.height / 2,
  speed: 0,
  maxSpeed: 5,
  accel: 0.1
};

/* =========================
   DATA
========================= */

const planetsList = [
  "Erebus","Cairn","Halide","Nyx","Orris",
  "Mim","Vela","Orbus","Kestra","Lumen",
  "Rift","Talon","Aster","Vale","Odin"
];

/* =========================
   SCENE STATE (FAST + EPHEMERAL)
========================= */

let currentScene = {
  text: "You are moving through a structure that does not announce itself."
};

let sceneTimer = null;
const SCENE_VISIBLE_MS = 1200; // ★ short-lived

function hideScene() {
  const screen = document.getElementById("screen");
  if (!screen) return;

  screen.classList.add("hidden");

  if (sceneTimer) {
    clearTimeout(sceneTimer);
    sceneTimer = null;
  }
}

function updateScene(text) {
  currentScene.text = text;

  const screen = document.getElementById("screen");
  const el = document.getElementById("sceneText");
  if (!screen || !el) return;

  el.textContent = text;
  screen.classList.remove("hidden");

  if (sceneTimer) clearTimeout(sceneTimer);

  sceneTimer = setTimeout(() => {
    hideScene();
  }, SCENE_VISIBLE_MS);
}

/* =========================
   BUBBLES
========================= */

const bubbles = [];
const TOTAL_BUBBLES = 600;

for (let i = 0; i < TOTAL_BUBBLES; i++) {
  bubbles.push({
    x: Math.random() * canvas.width - ship.x,
    y: Math.random() * canvas.height - ship.y,
    z: Math.random() * canvas.width,
    size: 3,
    speed: Math.random() * 0.5 + 0.1,
    word: planetsList[Math.floor(Math.random() * planetsList.length)],
    isFocused: false
  });
}

/* =========================
   CONTROLS
========================= */

const controls = {
  up: false,
  down: false,
  left: false,
  right: false,
  showLabels: true
};

let focusedBubble = null;

/* =========================
   INPUT
========================= */

document.addEventListener("keydown", e => {
  // ★ Any key acknowledges / dismisses scene
  hideScene();

  const key = e.key.toLowerCase();
  if (key.length === 1 && key >= "a" && key <= "z") {
    easterEggBuffer = (easterEggBuffer + key).slice(-EASTER_EGG_SEQUENCE.length);
    if (easterEggBuffer === EASTER_EGG_SEQUENCE) {
      openEasterEggPanel();
      easterEggBuffer = "";
    }
  }

  switch (key) {
    case "c": toggleControlPanel(); break;
    case "w": controls.up = true; break;
    case "s": controls.down = true; break;
    case "a": controls.left = true; break;
    case "d": controls.right = true; break;
    case "x": controls.showLabels = !controls.showLabels; break;
    case "g": location.reload(); break;
    case "escape": closeEasterEggPanel(); break;

    case " ":
      if (focusedBubble) {
        updateScene(
          `You focused on ${focusedBubble.word}.
This action cannot be undone.`
        );
      }
      break;
  }
});

document.addEventListener("keyup", e => {
  switch (e.key.toLowerCase()) {
    case "w": controls.up = false; break;
    case "s": controls.down = false; break;
    case "a": controls.left = false; break;
    case "d": controls.right = false; break;
  }
});

const closeEasterEgg = document.getElementById("closeEasterEgg");
if (closeEasterEgg) {
  closeEasterEgg.addEventListener("click", closeEasterEggPanel);
}

/* =========================
   UPDATE
========================= */

function update() {
  // Ship speed
  if (controls.up) {
    ship.speed = Math.min(ship.maxSpeed, ship.speed + ship.accel);
  }
  if (controls.down) {
    ship.speed = Math.max(0, ship.speed - ship.accel);
  }

  // Move bubbles
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

  // Focus detection
  focusedBubble = null;

  for (const b of bubbles) {
    const scale = canvas.width / b.z;
    const x = ship.x + b.x * scale;
    const y = ship.y + b.y * scale;

    const focused =
      Math.abs(x - canvas.width / 2) < 20 &&
      Math.abs(y - canvas.height / 2) < 20;

    b.isFocused = focused;

    if (focused && !focusedBubble) {
      focusedBubble = b;
    }
  }
}

/* =========================
   DRAW
========================= */

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

  // Reticle
  context.strokeStyle = "rgba(34,255,102,0.3)";
  context.beginPath();
  context.arc(canvas.width / 2, canvas.height / 2, 20, 0, Math.PI * 2);
  context.stroke();
}

/* =========================
   MAIN LOOP
========================= */

function loop() {
  update();
  draw();
  requestAnimationFrame(loop);
}

loop();

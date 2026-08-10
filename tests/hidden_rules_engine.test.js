const test = require("node:test");
const assert = require("node:assert/strict");
const { Engine, replayDeterministicSignature } = require("../hidden_rules_engine.js");

function runWords(engine, words) {
  for (const word of words) {
    engine.interact(word);
  }
}

test("deterministic replay signature for same seed/actions", () => {
  const words = ["Erebus", "Nyx", "Orris", "Erebus", "Nyx", "Orris", "Lumen"];
  const a = replayDeterministicSignature(12345, words);
  const b = replayDeterministicSignature(12345, words);
  assert.equal(a, b);
});

test("ordering dependence changes resulting history", () => {
  const a = new Engine({ seed: 42 });
  const b = new Engine({ seed: 42 });

  runWords(a, ["Erebus", "Nyx", "Erebus", "Nyx", "Lumen"]);
  runWords(b, ["Erebus", "Erebus", "Nyx", "Nyx", "Lumen"]);

  const aOrderEvents = a.state.history.filter((e) => e.type === "ORDER_ANOMALY").length;
  const bOrderEvents = b.state.history.filter((e) => e.type === "ORDER_ANOMALY").length;

  assert.notEqual(a.replaySignature(), b.replaySignature());
  assert.notEqual(aOrderEvents, bOrderEvents);
});

test("delayed consequence appears after causal lag", () => {
  const engine = new Engine({
    seed: 7,
    delayedLagMin: 3,
    delayedLagMax: 3,
    delayedExpiryWindow: 20
  });

  const before = engine.state.history.length;
  engine.interact("Erebus");
  engine.interact("Nyx");
  const immediateDelayed = engine.state.history.filter((e) => e.type === "DELAYED_EFFECT").length;
  assert.equal(immediateDelayed, 0);

  engine.interact("Orris");
  engine.interact("Lumen");
  const delayedAfterLag = engine.state.history.filter((e) => e.type === "DELAYED_EFFECT").length;
  assert.ok(engine.state.history.length > before);
  assert.ok(delayedAfterLag >= 1);
});

test("save/load persistence keeps lineage and replay stable", () => {
  const engine = new Engine({ seed: 555 });
  runWords(engine, ["Aster", "Vale", "Talon", "Aster", "Vale"]);

  const serialized = engine.serialize();
  const restored = Engine.fromSave(serialized);

  assert.equal(restored.state.lineageDepth, engine.state.lineageDepth);
  assert.equal(restored.state.turn, engine.state.turn);
  assert.deepEqual(restored.state.counters, engine.state.counters);
  assert.equal(restored.replaySignature(), engine.replaySignature());
});

test("forensic traces and ancestry links are preserved in export", () => {
  const engine = new Engine({
    seed: 11,
    delayedLagMin: 2,
    delayedLagMax: 2
  });
  runWords(engine, ["Erebus", "Nyx", "Lumen", "Orris", "Vela", "Mim"]);

  const exported = engine.exportLineage();
  assert.ok(Array.isArray(exported.events));
  assert.ok(Array.isArray(exported.actions));

  const hasForensic = exported.events.some((e) => e.forensic && typeof e.forensic.traceCode === "string");
  const hasAncestry = exported.events.some((e) => Array.isArray(e.parentEventIds) && e.parentEventIds.length > 0);
  assert.ok(hasForensic);
  assert.ok(hasAncestry);
});

test("lineage inheritance carries singular mutation into child lineage", () => {
  const engine = new Engine({
    seed: 99,
    delayedLagMin: 1,
    delayedLagMax: 1,
    singularityMinTurn: 5,
    singularityChance: 1,
    singularityResonanceThreshold: 0.4,
    singularityTensionThreshold: 0.4,
    singularityDelayedThreshold: 1
  });

  runWords(engine, ["Erebus", "Nyx", "Orris", "Lumen", "Talon", "Aster", "Vale"]);
  assert.equal(engine.state.worldFlags.singularityTriggered, true);

  const child = engine.createChildLineage();
  assert.equal(child.state.lineageDepth, engine.state.lineageDepth + 1);
  assert.equal(child.state.worldFlags.singularityTriggered, true);
  assert.equal(child.state.worldFlags.mutationFamilyId, "SM-01");
});

test("legacy lineage array is imported without corruption", () => {
  const legacy = [
    { type: "SEEN", label: "seen:core-conduit", t: 1 },
    { type: "POP", label: "activate-core", t: 2 }
  ];
  const engine = Engine.fromSave(legacy);
  assert.equal(engine.state.history.length, 2);
  assert.equal(engine.state.turn, 2);
  assert.equal(engine.state.history[0].kind, "LEGACY_EVENT");
});

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.HiddenRulesEngine = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function hashString(input) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < input.length; i++) {
      h ^= input.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function mulberry32(seed) {
    let t = seed >>> 0;
    return function () {
      t += 0x6d2b79f5;
      let r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function categoryForWord(word, shift) {
    const categories = ["alpha", "beta", "gamma"];
    const base = hashString(word) % categories.length;
    return categories[(base + shift) % categories.length];
  }

  function shallowCopy(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  class Engine {
    constructor(options = {}) {
      const now = Date.now();
      this.config = {
        singularityChance: options.singularityChance ?? 0.0045,
        singularityMinTurn: options.singularityMinTurn ?? 34,
        singularityResonanceThreshold: options.singularityResonanceThreshold ?? 2.2,
        singularityTensionThreshold: options.singularityTensionThreshold ?? 2.1,
        singularityDelayedThreshold: options.singularityDelayedThreshold ?? 2,
        delayedLagMin: options.delayedLagMin ?? 14,
        delayedLagMax: options.delayedLagMax ?? 32,
        delayedExpiryWindow: options.delayedExpiryWindow ?? 40
      };

      this.state = {
        version: 2,
        seed: options.seed ?? (now % 2147483647),
        lineageId: options.lineageId ?? `lineage-${now}`,
        lineageDepth: options.lineageDepth ?? 0,
        turn: options.turn ?? 0,
        encounterIndex: options.encounterIndex ?? 0,
        worldFlags: {
          singularityTriggered: false,
          mutationFamilyId: null,
          categoryShift: 0,
          delayedLagMultiplier: 1
        },
        latent: {
          resonance: 0,
          drift: 0,
          tension: 0,
          phase: 0
        },
        counters: {
          totalInteractions: 0,
          delayedTriggered: 0,
          delayedExpired: 0
        },
        memory: {
          wordCounts: {},
          categoryTrail: [],
          interactionTrail: [],
          ancestryAnchors: []
        },
        history: [],
        actions: []
      };

      this.rng = mulberry32(this.state.seed);
      this.nextEventId = 1;
    }

    static fromSave(save, options = {}) {
      if (Array.isArray(save)) {
        return Engine.fromLegacyEventArray(save, options);
      }

      const engine = new Engine({
        seed: save?.seed,
        lineageId: save?.lineageId,
        lineageDepth: save?.lineageDepth,
        turn: save?.turn,
        encounterIndex: save?.encounterIndex,
        singularityChance: options.singularityChance,
        singularityMinTurn: options.singularityMinTurn,
        singularityResonanceThreshold: options.singularityResonanceThreshold,
        singularityTensionThreshold: options.singularityTensionThreshold,
        singularityDelayedThreshold: options.singularityDelayedThreshold,
        delayedLagMin: options.delayedLagMin,
        delayedLagMax: options.delayedLagMax,
        delayedExpiryWindow: options.delayedExpiryWindow
      });

      if (!save || typeof save !== "object") return engine;

      const merged = shallowCopy(engine.state);
      merged.version = save.version ?? merged.version;
      merged.seed = save.seed ?? merged.seed;
      merged.lineageId = save.lineageId ?? merged.lineageId;
      merged.lineageDepth = save.lineageDepth ?? merged.lineageDepth;
      merged.turn = save.turn ?? merged.turn;
      merged.encounterIndex = save.encounterIndex ?? merged.encounterIndex;
      merged.worldFlags = {
        ...merged.worldFlags,
        ...(save.worldFlags || {})
      };
      merged.latent = {
        ...merged.latent,
        ...(save.latent || {})
      };
      merged.counters = {
        ...merged.counters,
        ...(save.counters || {})
      };
      merged.memory = {
        ...merged.memory,
        ...(save.memory || {})
      };
      merged.memory.wordCounts = merged.memory.wordCounts || {};
      merged.memory.categoryTrail = merged.memory.categoryTrail || [];
      merged.memory.interactionTrail = merged.memory.interactionTrail || [];
      merged.memory.ancestryAnchors = merged.memory.ancestryAnchors || [];
      merged.history = Array.isArray(save.history) ? save.history : [];
      merged.actions = Array.isArray(save.actions) ? save.actions : [];

      engine.state = merged;
      engine.rng = mulberry32(engine.state.seed);
      engine.reseedRngFromHistory();
      engine.nextEventId = engine.state.history.reduce((m, e) => Math.max(m, e.id || 0), 0) + 1;
      return engine;
    }

    static fromLegacyEventArray(events, options = {}) {
      const engine = new Engine(options);
      const normalized = Array.isArray(events) ? events : [];
      engine.state.history = normalized.map((e, index) => ({
        id: index + 1,
        turn: index + 1,
        ts: e.t ?? Date.now(),
        kind: "LEGACY_EVENT",
        label: e.label ?? "legacy-event",
        type: e.type ?? "UNKNOWN",
        bubbleWord: null,
        encounterIndex: null,
        ancestryDepth: 0,
        parentEventIds: [],
        ruleFamilyId: null,
        latentSnapshot: shallowCopy(engine.state.latent),
        forensic: {
          traceCode: `legacy-${index + 1}`,
          lagHint: null,
          ancestryPressure: 0,
          observables: {}
        }
      }));
      engine.state.turn = engine.state.history.length;
      engine.nextEventId = engine.state.history.length + 1;
      return engine;
    }

    reseedRngFromHistory() {
      const salt = this.state.history.length + this.state.actions.length + this.state.turn;
      this.rng = mulberry32((this.state.seed + salt) >>> 0);
    }

    emitEvent(partial) {
      const event = {
        id: this.nextEventId++,
        turn: this.state.turn,
        ts: Date.now(),
        kind: partial.kind,
        label: partial.label,
        type: partial.type,
        bubbleWord: partial.bubbleWord ?? null,
        encounterIndex: partial.encounterIndex ?? null,
        ancestryDepth: this.state.lineageDepth,
        parentEventIds: partial.parentEventIds ?? [],
        ruleFamilyId: partial.ruleFamilyId ?? null,
        latentSnapshot: {
          resonance: Number(this.state.latent.resonance.toFixed(3)),
          drift: Number(this.state.latent.drift.toFixed(3)),
          tension: Number(this.state.latent.tension.toFixed(3)),
          phase: Number(this.state.latent.phase.toFixed(3))
        },
        forensic: partial.forensic || {
          traceCode: `f-${hashString(`${partial.label}:${this.state.turn}`) % 100000}`,
          lagHint: null,
          ancestryPressure: this.state.memory.ancestryAnchors.length,
          observables: {}
        }
      };
      this.state.history.push(event);
      return event;
    }

    interact(word, context = {}) {
      this.state.turn += 1;
      this.state.encounterIndex += 1;
      this.state.counters.totalInteractions += 1;

      const category = categoryForWord(word, this.state.worldFlags.categoryShift);
      const wCounts = this.state.memory.wordCounts;
      wCounts[word] = (wCounts[word] || 0) + 1;
      const countForWord = wCounts[word];
      this.state.memory.categoryTrail.push(category);
      this.state.memory.interactionTrail.push(word);
      this.state.memory.categoryTrail = this.state.memory.categoryTrail.slice(-16);
      this.state.memory.interactionTrail = this.state.memory.interactionTrail.slice(-40);

      this.state.actions.push({
        turn: this.state.turn,
        action: "INTERACT",
        word,
        encounterIndex: this.state.encounterIndex
      });

      const actionEvent = this.emitEvent({
        kind: "ACTION",
        label: "encounter-acted",
        type: "INTERACT",
        bubbleWord: word,
        encounterIndex: this.state.encounterIndex,
        forensic: {
          traceCode: `a-${hashString(`${word}:${this.state.turn}`) % 100000}`,
          lagHint: null,
          ancestryPressure: this.state.memory.ancestryAnchors.length,
          observables: {
            category,
            countForWord
          }
        }
      });

      this.state.latent.resonance += category === "alpha" ? 0.25 : 0.14;
      this.state.latent.tension += category === "gamma" ? 0.22 : 0.08;
      this.state.latent.drift += (hashString(word) % 7 - 3) * 0.03;
      this.state.latent.phase += (hashString(`${word}:${this.state.turn}`) % 19 - 9) * 0.02;

      const produced = [actionEvent];

      produced.push(...this.applySimpleRegularities(word, category, countForWord, actionEvent.id));
      produced.push(...this.applyOrderRegularities(word, category, actionEvent.id));
      produced.push(...this.applyDepthRegularities(word, category, actionEvent.id));
      produced.push(...this.resolveDelayedPredicates(word, category, actionEvent.id));
      produced.push(...this.applyStatisticalRegularities(word, category, actionEvent.id));
      produced.push(...this.applyEmergentRegularities(word, category, actionEvent.id));
      produced.push(...this.applySingularityMutation(word, category, actionEvent.id));

      this.applyMutationAftereffects(category);

      return {
        events: produced,
        stateSnapshot: this.getPublicSnapshot()
      };
    }

    applySimpleRegularities(word, category, countForWord, parentId) {
      const out = [];
      if (countForWord % 3 === 0) {
        out.push(this.emitEvent({
          kind: "CONSEQUENCE",
          label: "echo-bloom",
          type: "ECHO",
          bubbleWord: word,
          encounterIndex: this.state.encounterIndex,
          parentEventIds: [parentId],
          ruleFamilyId: "RF-A1",
          forensic: {
            traceCode: `rf-a1-${countForWord}`,
            lagHint: null,
            ancestryPressure: this.state.memory.ancestryAnchors.length,
            observables: {
              category,
              repetitionBand: Math.floor(countForWord / 3)
            }
          }
        }));
      }

      const lagBase = this.config.delayedLagMin + Math.floor(this.rng() * (this.config.delayedLagMax - this.config.delayedLagMin + 1));
      const lag = Math.floor(lagBase * this.state.worldFlags.delayedLagMultiplier);
      this.state.memory.ancestryAnchors.push({
        anchorId: `an-${parentId}`,
        sourceEventId: parentId,
        sourceTurn: this.state.turn,
        sourceCategory: category,
        minTurn: this.state.turn + lag,
        expiresTurn: this.state.turn + lag + this.config.delayedExpiryWindow,
        sourceWord: word,
        consumed: false
      });

      return out;
    }

    applyOrderRegularities(word, category, parentId) {
      const out = [];
      const trail = this.state.memory.categoryTrail;
      if (trail.length >= 4) {
        const a = trail[trail.length - 4];
        const b = trail[trail.length - 3];
        const c = trail[trail.length - 2];
        const d = trail[trail.length - 1];
        if (a === c && b === d && a !== b) {
          out.push(this.emitEvent({
            kind: "ANOMALY_HINT",
            label: "ordering-knot",
            type: "ORDER_ANOMALY",
            bubbleWord: word,
            encounterIndex: this.state.encounterIndex,
            parentEventIds: [parentId],
            ruleFamilyId: "RF-ORD2",
            forensic: {
              traceCode: `rf-ord2-${hashString(`${a}${b}${c}${d}`) % 9999}`,
              lagHint: null,
              ancestryPressure: this.state.memory.ancestryAnchors.length,
              observables: { trailTail: [a, b, c, d] }
            }
          }));
        }
      }
      return out;
    }

    applyDepthRegularities(word, category, parentId) {
      const out = [];
      const pressure = this.state.lineageDepth * 0.8 + this.state.counters.totalInteractions / 22;
      if (pressure > 1.8 && this.state.turn % 5 === 0) {
        this.state.latent.tension += 0.18;
        out.push(this.emitEvent({
          kind: "TRACE",
          label: "ancestral-shear",
          type: "DEPTH_EFFECT",
          bubbleWord: word,
          encounterIndex: this.state.encounterIndex,
          parentEventIds: [parentId],
          ruleFamilyId: "RF-LDEP3",
          forensic: {
            traceCode: `rf-ldep3-${Math.floor(pressure * 100)}`,
            lagHint: null,
            ancestryPressure: Number(pressure.toFixed(3)),
            observables: {
              category,
              turnBand: Math.floor(this.state.turn / 5)
            }
          }
        }));
      }
      return out;
    }

    resolveDelayedPredicates(word, category, parentId) {
      const out = [];
      for (const anchor of this.state.memory.ancestryAnchors) {
        if (anchor.consumed) continue;
        if (this.state.turn < anchor.minTurn) continue;
        if (this.state.turn > anchor.expiresTurn) {
          anchor.consumed = true;
          this.state.counters.delayedExpired += 1;
          out.push(this.emitEvent({
            kind: "TRACE",
            label: "ancestral-evaporation",
            type: "DELAYED_EXPIRE",
            bubbleWord: word,
            encounterIndex: this.state.encounterIndex,
            parentEventIds: [parentId, anchor.sourceEventId],
            ruleFamilyId: "RF-DL1",
            forensic: {
              traceCode: `rf-dl1-exp-${anchor.sourceEventId}`,
              lagHint: this.state.turn - anchor.sourceTurn,
              ancestryPressure: this.state.memory.ancestryAnchors.length,
              observables: { sourceCategory: anchor.sourceCategory }
            }
          }));
          continue;
        }

        const mismatch = category !== anchor.sourceCategory;
        const tensionGate = (this.state.latent.tension + this.state.latent.resonance) > 1.65;
        if (mismatch && tensionGate) {
          anchor.consumed = true;
          this.state.counters.delayedTriggered += 1;
          this.state.latent.phase += 0.22;
          out.push(this.emitEvent({
            kind: "CONSEQUENCE",
            label: "ancestral-interference",
            type: "DELAYED_EFFECT",
            bubbleWord: word,
            encounterIndex: this.state.encounterIndex,
            parentEventIds: [parentId, anchor.sourceEventId],
            ruleFamilyId: "RF-DL1",
            forensic: {
              traceCode: `rf-dl1-${anchor.sourceEventId}`,
              lagHint: this.state.turn - anchor.sourceTurn,
              ancestryPressure: this.state.memory.ancestryAnchors.length,
              observables: {
                sourceWord: anchor.sourceWord,
                sourceCategory: anchor.sourceCategory,
                triggerCategory: category
              }
            }
          }));
        }
      }

      this.state.memory.ancestryAnchors = this.state.memory.ancestryAnchors.filter((a) => !a.consumed);
      return out;
    }

    applyStatisticalRegularities(word, category, parentId) {
      const out = [];
      const latentSignal =
        this.state.latent.phase * 0.8 +
        this.state.latent.drift * 0.35 +
        (hashString(`${word}:${this.state.turn}:${this.state.seed}`) % 1000) / 1000;
      const normalized = 1 / (1 + Math.exp(-latentSignal));
      const threshold = 0.92 - clamp(this.state.lineageDepth * 0.03, 0, 0.15);
      if (normalized > threshold) {
        out.push(this.emitEvent({
          kind: "ANOMALY_HINT",
          label: "phase-scatter",
          type: "STAT_EFFECT",
          bubbleWord: word,
          encounterIndex: this.state.encounterIndex,
          parentEventIds: [parentId],
          ruleFamilyId: "RF-STAT4",
          forensic: {
            traceCode: `rf-stat4-${Math.floor(normalized * 1000)}`,
            lagHint: null,
            ancestryPressure: this.state.memory.ancestryAnchors.length,
            observables: {
              category,
              latentBand: Math.floor(normalized * 10),
              lineageDepth: this.state.lineageDepth
            }
          }
        }));
      }
      return out;
    }

    applyEmergentRegularities(word, category, parentId) {
      const out = [];
      const startsVowel = /^[aeiou]/i.test(word);
      const deeperGate =
        (startsVowel && category === "beta" && this.state.latent.resonance > 1.15) ||
        (!startsVowel && this.state.latent.drift > 0.7 && this.state.latent.tension > 1.1);

      if (deeperGate) {
        out.push(this.emitEvent({
          kind: "CONSEQUENCE",
          label: "flare-bloom",
          type: "EMERGENT_EFFECT",
          bubbleWord: word,
          encounterIndex: this.state.encounterIndex,
          parentEventIds: [parentId],
          ruleFamilyId: "RF-EM5",
          forensic: {
            traceCode: `rf-em5-${startsVowel ? "v" : "c"}-${category}`,
            lagHint: null,
            ancestryPressure: this.state.memory.ancestryAnchors.length,
            observables: {
              apparentPattern: startsVowel ? "vowel" : "nonvowel",
              category
            }
          }
        }));
      }
      return out;
    }

    applySingularityMutation(word, category, parentId) {
      if (this.state.worldFlags.singularityTriggered) return [];
      if (this.state.turn < this.config.singularityMinTurn) return [];
      if (this.state.counters.delayedTriggered < this.config.singularityDelayedThreshold) return [];
      if (this.state.latent.resonance < this.config.singularityResonanceThreshold) return [];
      if (this.state.latent.tension < this.config.singularityTensionThreshold) return [];

      if (this.rng() >= this.config.singularityChance) return [];

      this.state.worldFlags.singularityTriggered = true;
      this.state.worldFlags.mutationFamilyId = "SM-01";
      this.state.worldFlags.categoryShift = 1;
      this.state.worldFlags.delayedLagMultiplier = 1.75;
      this.state.latent.phase += 1.2;

      return [this.emitEvent({
        kind: "HISTORICAL_SINGULARITY",
        label: "chronoclastic-fold",
        type: "SINGULARITY",
        bubbleWord: word,
        encounterIndex: this.state.encounterIndex,
        parentEventIds: [parentId],
        ruleFamilyId: "SM-01",
        forensic: {
          traceCode: "sm-01",
          lagHint: null,
          ancestryPressure: this.state.memory.ancestryAnchors.length,
          observables: {
            categoryBeforeMutation: category
          }
        }
      })];
    }

    applyMutationAftereffects(category) {
      if (!this.state.worldFlags.singularityTriggered) {
        this.state.latent.resonance *= 0.997;
        this.state.latent.tension *= 0.996;
        return;
      }

      if (category === "beta") {
        this.state.latent.resonance += 0.06;
      } else if (category === "alpha") {
        this.state.latent.tension += 0.05;
      }
      this.state.latent.phase += 0.015;
    }

    createChildLineage() {
      const child = new Engine({
        seed: (this.state.seed + hashString(this.state.lineageId)) >>> 0,
        lineageDepth: this.state.lineageDepth + 1
      });
      child.state.worldFlags = shallowCopy(this.state.worldFlags);
      child.state.latent = {
        resonance: this.state.latent.resonance * 0.35,
        drift: this.state.latent.drift * 0.35,
        tension: this.state.latent.tension * 0.35,
        phase: this.state.latent.phase * 0.35
      };
      child.state.history = [];
      child.state.actions = [];
      return child;
    }

    serialize() {
      return shallowCopy(this.state);
    }

    getPublicSnapshot() {
      return {
        lineageId: this.state.lineageId,
        lineageDepth: this.state.lineageDepth,
        turn: this.state.turn,
        encounterIndex: this.state.encounterIndex,
        latent: shallowCopy(this.state.latent),
        worldFlags: shallowCopy(this.state.worldFlags),
        counters: shallowCopy(this.state.counters)
      };
    }

    exportLineage() {
      return {
        version: this.state.version,
        lineage: {
          id: this.state.lineageId,
          depth: this.state.lineageDepth,
          seed: this.state.seed
        },
        observability: {
          note: "Not all causal state is visible in present-state observables; use ancestry links and event order for reconstruction."
        },
        stateSnapshot: this.getPublicSnapshot(),
        actions: shallowCopy(this.state.actions),
        events: shallowCopy(this.state.history)
      };
    }

    replaySignature() {
      const base = this.state.history.map((e) =>
        `${e.turn}|${e.type}|${e.label}|${e.ruleFamilyId || "-"}`.trim()
      ).join(";");
      return hashString(base).toString(16);
    }
  }

  function replayDeterministicSignature(seed, words, options = {}) {
    const engine = new Engine({ seed, ...options });
    for (const word of words) {
      engine.interact(word);
    }
    return engine.replaySignature();
  }

  return {
    Engine,
    replayDeterministicSignature
  };
});

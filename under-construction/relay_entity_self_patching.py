"""
relay_entity_self_patching.py

Implements the generalized self-patching scan proposed in "Admissibility
Unchained: Relay Entities and the Time of Generalization" (companion to
"Knowing Without Using: The Fine-Tuning Gap as an Admissibility Defect").

Dai et al. (arXiv:2607.08393) anchor every self-patching scan at the
head-entity token position. This script generalizes their intervention
so the same machinery can be run a second time, anchored instead at the
relay entity (their "bridge entity"), for chaining instances specifically.
Running both scans across the same checkpoints produces two permeation
maps per instance rather than one, from which the two interface times
T_{A->B} and T_{B->C} can be estimated separately, rather than only
their maximum as the original study's aggregate accuracy curves report.

This is written against TransformerLens's HookedTransformer API. It is
NOT tied to any specific released checkpoint set -- Dai et al.'s own
checkpoints are not (as of writing) known to be publicly hosted, so the
CheckpointSweep class here is a loader stub: point it at whatever
directory of per-epoch state dicts your own fine-tuning run produces.

Usage sketch:

    model = HookedTransformer.from_pretrained("Qwen/Qwen2.5-1.5B")
    instance = ChainingInstance(
        head_entity="Sydney", relay_entity="Australia", answer="Canberra",
        gen_prompt="What is the capital of the country in which Sydney is located?",
    )
    sweep = CheckpointSweep(checkpoint_dir="runs/qwen1.5b_stark_prime/")
    head_maps, relay_maps = run_dual_anchor_sweep(model, instance, sweep)
    plot_permeation_series(head_maps, relay_maps, instance, out_dir="figs/")
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np
import torch
from transformer_lens import HookedTransformer
from transformer_lens.hook_points import HookPoint


# ---------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------

@dataclasses.dataclass
class ChainingInstance:
    """A single chaining instance: A -> B -> C, per Dai et al. Table 1."""

    head_entity: str          # A
    relay_entity: str         # B, their "bridge entity"
    answer: str                # C
    gen_prompt: str            # the composed, never-trained-on query
    mem_prompt_1: Optional[str] = None  # "What is B related to A?" (optional,
    mem_prompt_2: Optional[str] = None  # for sanity-checking memorization)


AnchorKind = str  # "head" or "relay"


# ---------------------------------------------------------------------
# Anchor localization
# ---------------------------------------------------------------------

def find_entity_token_span(
    model: HookedTransformer, prompt: str, entity_str: str
) -> list[int]:
    """Return the token indices in `prompt` occupied by `entity_str`.

    Uses a simple substring match over the detokenized prompt. This is
    adequate for the STaRK-derived entity names used in the original
    study (concise biomedical terms, author/paper/field names) but should
    be checked against your tokenizer's actual splitting behavior for
    multi-token entity names with unusual casing or punctuation.
    """
    tokens = model.to_tokens(prompt)[0]
    str_tokens = model.to_str_tokens(prompt)

    # Reconstruct cumulative character offsets so we can align the
    # entity substring to a token span rather than assuming word
    # boundaries coincide with token boundaries.
    offsets = []
    running = 0
    for tok in str_tokens:
        offsets.append((running, running + len(tok)))
        running += len(tok)
    full_text = "".join(str_tokens)

    start_char = full_text.find(entity_str)
    if start_char == -1:
        raise ValueError(
            f"Entity string {entity_str!r} not found in tokenized prompt "
            f"{prompt!r}. Check for tokenizer-introduced casing/whitespace "
            f"differences."
        )
    end_char = start_char + len(entity_str)

    span = [
        i for i, (s, e) in enumerate(offsets)
        if s < end_char and e > start_char
    ]
    if not span:
        raise ValueError(f"Could not resolve token span for {entity_str!r}.")
    return span


def anchor_position(
    model: HookedTransformer,
    instance: ChainingInstance,
    prompt: str,
    anchor: AnchorKind,
) -> int:
    """Resolve the single anchor token position self-patching reads/writes.

    Following Dai et al.'s own token-position ablation (their Table 5),
    the anchor is taken as the *last* token of the entity span, which is
    the position their entity-position result is strongest for.
    """
    entity_str = instance.head_entity if anchor == "head" else instance.relay_entity
    span = find_entity_token_span(model, prompt, entity_str)
    return span[-1]


# ---------------------------------------------------------------------
# Core intervention: cache a source representation, patch it into a target
# ---------------------------------------------------------------------

def cache_source_activation(
    model: HookedTransformer, prompt: str, layer: int, token_pos: int
) -> torch.Tensor:
    """Run `prompt` and return the residual-stream state at (layer, token_pos).

    Uses resid_post, matching the "hidden layer representation" self-patching
    is defined over in the source paper's Algorithm 1.
    """
    _, cache = model.run_with_cache(prompt)
    resid = cache["resid_post", layer]  # [batch, seq, d_model]
    return resid[0, token_pos, :].detach().clone()


def patched_run(
    model: HookedTransformer,
    target_prompt: str,
    layer: int,
    token_pos: int,
    patch_vector: torch.Tensor,
) -> torch.Tensor:
    """Run `target_prompt` with resid_post at (layer, token_pos) overwritten.

    Returns the final-token logits of the patched run. This implements
    rho_{i->j}(z^(i)) = z~^(j) from the essay: the substituted vector is
    explicitly a *patched configuration*, not a claim that it equals
    whatever the model's own computation would natively produce at
    (layer, token_pos).
    """

    def hook_fn(resid: torch.Tensor, hook: HookPoint) -> torch.Tensor:
        resid[0, token_pos, :] = patch_vector
        return resid

    hook_name = f"blocks.{layer}.hook_resid_post"
    logits = model.run_with_hooks(
        target_prompt, fwd_hooks=[(hook_name, hook_fn)]
    )
    return logits[0, -1, :]  # final-position logits, unpatched decoding position


def unpatched_logits(model: HookedTransformer, prompt: str) -> torch.Tensor:
    logits = model(prompt)
    return logits[0, -1, :]


# ---------------------------------------------------------------------
# Correctness / indicator function
# ---------------------------------------------------------------------

def answer_log_prob(
    model: HookedTransformer, logits: torch.Tensor, answer: str
) -> float:
    """log P(answer's first token | prompt), matching the paper's use of
    exact match / a token-level indicator rather than full-sequence scoring.
    For multi-token answers, extend this to a teacher-forced sequence score;
    left as first-token scoring here to keep the scan cheap across the full
    layer-pair grid.
    """
    answer_token_id = model.to_tokens(answer, prepend_bos=False)[0, 0].item()
    log_probs = torch.log_softmax(logits, dim=-1)
    return log_probs[answer_token_id].item()


def indicator_delta(
    model: HookedTransformer,
    baseline_logits: torch.Tensor,
    patched_logits: torch.Tensor,
    answer: str,
) -> float:
    """Delta-I as in Algorithm 1: change in the correctness indicator.

    Reports the change in log P(answer), matching the Mean-Reciprocal-Rank
    -style scoring the original study allows as an alternative to strict
    exact match; swap in exact-match delta if you want a stricter statistic.
    """
    baseline = answer_log_prob(model, baseline_logits, answer)
    patched = answer_log_prob(model, patched_logits, answer)
    return patched - baseline


# ---------------------------------------------------------------------
# Single-anchor scan: the generalized version of Dai et al. Algorithm 1
# ---------------------------------------------------------------------

def self_patch_scan(
    model: HookedTransformer,
    instance: ChainingInstance,
    anchor: AnchorKind,
    n_layers: Optional[int] = None,
) -> np.ndarray:
    """Scan all (l_src, l_tgt) pairs for the given anchor, on this instance.

    anchor="head"  reproduces Dai et al.'s own scan.
    anchor="relay" is the extension this essay proposes: identical
                   machinery, different anchor token, run on the same
                   generalization prompt.

    Returns an (L, L) matrix A[l_src, l_tgt] = delta-I, matching the
    permeation-map convention of the source paper's Figure 4.
    """
    L = n_layers or model.cfg.n_layers
    result = np.zeros((L, L), dtype=np.float32)

    source_prompt = instance.gen_prompt
    target_prompt = instance.gen_prompt
    source_pos = anchor_position(model, instance, source_prompt, anchor)
    target_pos = anchor_position(model, instance, target_prompt, anchor)

    baseline_logits = unpatched_logits(model, target_prompt)

    for l_src in range(L):
        z_source = cache_source_activation(model, source_prompt, l_src, source_pos)
        for l_tgt in range(L):
            patched_logits = patched_run(
                model, target_prompt, l_tgt, target_pos, z_source
            )
            result[l_src, l_tgt] = indicator_delta(
                model, baseline_logits, patched_logits, instance.answer
            )

    return result


def run_dual_anchor_scan(
    model: HookedTransformer, instance: ChainingInstance
) -> tuple[np.ndarray, np.ndarray]:
    """Convenience wrapper: run both the head-entity and relay-entity scans
    on the same checkpoint and instance, as Section 3 of the essay proposes.
    """
    head_map = self_patch_scan(model, instance, anchor="head")
    relay_map = self_patch_scan(model, instance, anchor="relay")
    return head_map, relay_map


# ---------------------------------------------------------------------
# Checkpoint sweep: reproduce the training-dynamics permeation maps
# (Section 5.2 / Figure 4 of the source paper), per anchor
# ---------------------------------------------------------------------

class CheckpointSweep:
    """Loader stub over a directory of per-epoch fine-tuning checkpoints.

    Expects `checkpoint_dir` to contain files loadable via
    `model.load_state_dict(torch.load(path))`, named so that sorting the
    directory listing gives epoch order (e.g. epoch_000.pt, epoch_001.pt,
    ...). Adjust `load_checkpoint` to match your own training pipeline's
    checkpoint format if it differs (e.g. LoRA adapter weights rather than
    full state dicts).
    """

    def __init__(self, checkpoint_dir: str | Path):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.paths = sorted(self.checkpoint_dir.glob("*.pt"))
        if not self.paths:
            raise FileNotFoundError(
                f"No checkpoint files found in {self.checkpoint_dir}"
            )

    def __len__(self) -> int:
        return len(self.paths)

    def load_checkpoint(self, model: HookedTransformer, index: int) -> None:
        state_dict = torch.load(self.paths[index], map_location=model.cfg.device)
        model.load_state_dict(state_dict, strict=False)


def run_dual_anchor_sweep(
    model: HookedTransformer,
    instance: ChainingInstance,
    sweep: CheckpointSweep,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Run the dual-anchor scan at every checkpoint in `sweep`.

    Returns (head_maps, relay_maps), each a list of per-epoch (L, L)
    matrices, directly analogous to the epoch-indexed heatmap sequence
    in the source paper's Figure 4, but now available for both anchors
    rather than only the head entity.
    """
    head_maps: list[np.ndarray] = []
    relay_maps: list[np.ndarray] = []
    for epoch in range(len(sweep)):
        sweep.load_checkpoint(model, epoch)
        with torch.no_grad():
            head_map, relay_map = run_dual_anchor_scan(model, instance)
        head_maps.append(head_map)
        relay_maps.append(relay_map)
    return head_maps, relay_maps


# ---------------------------------------------------------------------
# Frontier extraction: turn a permeation-map sequence into an estimated T_k
# ---------------------------------------------------------------------

def diagonal_coverage(matrix: np.ndarray, threshold: float, band: int = 1) -> float:
    """Fraction of near-diagonal cells with delta-I above `threshold`.

    A coarse proxy for "the red region has reached the diagonal" (Section
    5.2 of the source paper's qualitative description). `band` widens the
    diagonal neighborhood considered, since the effective width of the
    naturally-successful region need not be exactly one cell.
    """
    L = matrix.shape[0]
    hits, total = 0, 0
    for i in range(L):
        for j in range(max(0, i - band), min(L, i + band + 1)):
            total += 1
            if matrix[i, j] > threshold:
                hits += 1
    return hits / total if total else 0.0


def estimate_interface_time(
    maps_over_epochs: list[np.ndarray],
    threshold: float = 0.5,
    coverage_target: float = 0.5,
    stability_window: int = 2,
) -> Optional[int]:
    """Estimate T_k as the earliest epoch at which diagonal coverage exceeds
    `coverage_target` and stays there for `stability_window` epochs.

    This mirrors the saturation-time definition in the source paper (their
    Eq. 2): the first checkpoint after which performance is stable for w
    consecutive epochs, rather than the first epoch that merely touches the
    target once and regresses.
    """
    coverages = [diagonal_coverage(m, threshold) for m in maps_over_epochs]
    for t in range(len(coverages) - stability_window + 1):
        window = coverages[t : t + stability_window]
        if all(c >= coverage_target for c in window):
            return t
    return None  # never stably reaches the diagonal: a "halted" instance


def classify_instance(
    head_maps: list[np.ndarray], relay_maps: list[np.ndarray]
) -> dict:
    """Estimate T_{A->B}, T_{B->C}, and bucket the instance into the
    three-class taxonomy from Section 4 of the essay.

    T_{A->B} is read off the head-entity scan's own diagonal frontier
    (does the head entity's representation reach a form the *first*
    retrieval step can use); T_{B->C} is read off the relay-entity scan's
    diagonal frontier on the *composed* generalization prompt. Both are
    approximations -- a cleaner separation would score the two hops
    against their own intermediate targets rather than only the final
    answer, which the answer_log_prob scoring here does not yet do; see
    the TODO below.
    """
    t_ab = estimate_interface_time(head_maps)
    t_bc = estimate_interface_time(relay_maps)

    if t_ab is None or t_bc is None:
        bucket = "unresolved"
    elif t_ab > t_bc:
        bucket = "head_to_relay_bottleneck"
    elif t_ab < t_bc:
        bucket = "relay_to_answer_bottleneck"
    else:
        bucket = "co_limiting"

    return {"T_AB": t_ab, "T_BC": t_bc, "class": bucket}

    # TODO: as written, both estimate_interface_time calls score against
    # the *final* answer, since answer_log_prob is defined over
    # `instance.answer` only. A more faithful T_{A->B} estimate would
    # score the head-entity scan against the relay entity's own identity
    # (i.e. does patching make the model's *intermediate* prediction of B
    # correct), which requires a second indicator function keyed to
    # instance.relay_entity rather than instance.answer. Left as the
    # natural next refinement once this scaffold is validated end to end.


# ---------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------

def plot_permeation_heatmap(matrix: np.ndarray, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1, origin="lower")
    ax.plot([0, matrix.shape[0] - 1], [0, matrix.shape[0] - 1], color="black",
            linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_xlabel("target layer")
    ax.set_ylabel("source layer")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=r"$\Delta I$")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_permeation_series(
    head_maps: list[np.ndarray],
    relay_maps: list[np.ndarray],
    instance: ChainingInstance,
    out_dir: str | Path,
) -> None:
    """Write one heatmap per epoch per anchor, matching the source paper's
    Figure 4 layout, but producing two rows (head, relay) instead of one.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for epoch, (head_map, relay_map) in enumerate(zip(head_maps, relay_maps)):
        plot_permeation_heatmap(
            head_map,
            f"head anchor, epoch {epoch}",
            out_dir / f"head_epoch{epoch:03d}.png",
        )
        plot_permeation_heatmap(
            relay_map,
            f"relay anchor, epoch {epoch}",
            out_dir / f"relay_epoch{epoch:03d}.png",
        )


# ---------------------------------------------------------------------
# Example driver
# ---------------------------------------------------------------------

if __name__ == "__main__":
    model = HookedTransformer.from_pretrained("Qwen/Qwen2.5-1.5B")
    model.eval()

    instance = ChainingInstance(
        head_entity="Sydney",
        relay_entity="Australia",
        answer="Canberra",
        gen_prompt="What is the capital of the country in which Sydney is located?",
    )

    sweep = CheckpointSweep(checkpoint_dir="runs/qwen1.5b_stark_prime/")
    head_maps, relay_maps = run_dual_anchor_sweep(model, instance, sweep)

    result = classify_instance(head_maps, relay_maps)
    print(f"T_A->B = {result['T_AB']}, T_B->C = {result['T_BC']}, "
          f"class = {result['class']}")

    plot_permeation_series(head_maps, relay_maps, instance, out_dir="figs/")

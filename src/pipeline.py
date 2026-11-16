
"""YOUR PoC PIPELINE — this is the file your group owns.

Lab contract = 5 automated steps, run by `python -m src.main ...`:
    01 load      input + provenance check (manifest.csv)
    02 process   your algorithm / model (the research part)
    03 rank      prioritise for a fixed review budget B
    04 review    human-in-the-loop: queue -> reviewer decisions -> overrides + audit log
    05 decide    GO / HOLD / REWORK (or track equivalent) with reason_code + owner, write outputs

Required output: out/<pred_file> with the columns listed for your track in
docs/tracks/TXX.md (also in src/metrics/tracks.py::TRACKS). Then evaluate with
    python -m src.evaluate --track tXX --pred out/<pred_file>

Rules: never read fixtures/*/gt/ here (the GT guard will stop you); seed everything via ctx.rng;
no network calls; fail loudly on missing models instead of downloading.
See src/examples/random_baseline.py for a minimal end-to-end wiring example.
"""
from __future__ import annotations

import pandas as pd

from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.manifest import verify_manifest
from .common.review import (
    load_review_decisions,
    make_review_queue,
    write_review_queue,
)
from .common.contact_sheet import render_contact_sheet
from .metrics.tracks import get_track

from .t02_scoring import (
    extract_dataset_features,
    score_blur_dark,
)


# ---------------------------------------------------------------- 01 load
def load(ctx: RunContext) -> dict:
    """Load T02 metadata and verify input provenance."""

    # 1. Verify data provenance using manifest.csv
    manifest_path = ctx.input_dir / "manifest.csv"

    problems = (
        verify_manifest(manifest_path)
        if manifest_path.exists()
        else [{"problem": "no_manifest"}]
    )

    if problems:
        ctx.audit.log(
            actor="pipeline",
            action="provenance_problems",
            item_id=str(manifest_path),
            after=problems[:20],
        )

        if ctx.config.get("strict_provenance", True):
            raise ValueError(
                f"provenance check failed ({len(problems)} problems), "
                f"first: {problems[:3]}"
            )

    # 2. Load manifest
    manifest = (
        pd.read_csv(manifest_path)
        if manifest_path.exists()
        else None
    )

    # 3. Load image metadata
    images_path = ctx.input_dir / "images.csv"

    if not images_path.exists():
        raise FileNotFoundError(
            f"Missing images.csv: {images_path}"
        )

    images = pd.read_csv(images_path)

    # 4. Validate required columns
    required_columns = [
        "image_id",
        "path",
        "camera_id",
        "light",
        "split",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in images.columns
    ]

    if missing_columns:
        raise ValueError(
            f"images.csv is missing columns: {missing_columns}"
        )

    # 5. Validate image IDs
    if images["image_id"].isna().any():
        raise ValueError("images.csv contains missing image_id")

    if images["image_id"].duplicated().any():
        raise ValueError("images.csv contains duplicate image_id")

    # 6. Validate image paths
    missing_images = []

    for relative_path in images["path"]:
        image_path = ctx.input_dir / str(relative_path)

        if not image_path.is_file():
            missing_images.append(str(image_path))

    if missing_images:
        raise FileNotFoundError(
            f"Missing {len(missing_images)} image files. "
            f"First missing files: {missing_images[:5]}"
        )

    # 7. Return loaded data
    return {
        "manifest": manifest,
        "images": images,
    }


# ---------------------------------------------------------------- 02 process
def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    """Extract and score Blur/Dark features for T02."""

    spec = get_track(ctx.track)

    if spec.track != "t02":
        raise NotImplementedError(
            f"Blur/Dark processing is only implemented for T02, "
            f"not {spec.track}"
        )

    if "images" not in data:
        raise ValueError(
            "process(): missing images metadata from load()"
        )

    # 1. Extract image features.
    features = extract_dataset_features(
        images=data["images"],
        input_dir=ctx.input_dir,
    )

    # 2. Calculate scores using DEV-only Blur references.
    scored = score_blur_dark(
        features=features,
        dev_split=ctx.param("dev_split", "dev"),
        min_group_size=int(ctx.param("min_group_size", 10)),
    )

    # 3. Preserve original relative image paths for human review.
    scored = scored.merge(
        data["images"][["image_id", "path"]],
        on="image_id",
        how="left",
        validate="one_to_one",
    )

    if scored["path"].isna().any():
        raise ValueError(
            "process(): missing image paths after metadata merge"
        )

    # 4. Combine Blur and Dark suspicion scores.
    scored["score"] = scored[
        ["blur_score", "dark_score"]
    ].max(axis=1)

    # 5. Validate output.
    required_columns = {"image_id", "score"}
    missing = required_columns - set(scored.columns)

    if missing:
        raise ValueError(
            f"process(): missing output columns: {sorted(missing)}"
        )

    if scored["image_id"].duplicated().any():
        raise ValueError(
            "process(): duplicate image_id in output"
        )

    if not scored["score"].map(
        lambda value: pd.notna(value) and 0 <= value <= 1
    ).all():
        raise ValueError(
            "process(): invalid score values"
        )

    ctx.stats["n_processed"] = len(scored)
    ctx.stats["scoring_method"] = "max_blur_dark_v1"

    return scored


# ---------------------------------------------------------------- 03 rank
def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    """Rank suspicious T02 images and create a human-review contact sheet."""

    budget = int(ctx.param("budget", 20))

    if budget < 1:
        raise ValueError("rank(): budget must be >= 1")

    required_columns = {
        "image_id",
        "score",
        "blur_score",
        "dark_score",
        "camera_id",
        "light",
        "path",
    }

    missing = required_columns - set(scored.columns)

    if missing:
        raise ValueError(
            f"rank(): missing required columns: {sorted(missing)}"
        )

    # Work on a copy; do not modify the original scored DataFrame.
    ranked_input = scored.copy()

    # 1. Identify the dominant suspicion feature.
    ranked_input["reason"] = "blur_dark"

    ranked_input.loc[
        ranked_input["blur_score"] > ranked_input["dark_score"],
        "reason",
    ] = "blur"

    ranked_input.loc[
        ranked_input["dark_score"] > ranked_input["blur_score"],
        "reason",
    ] = "dark"

    # 2. Human review is required.
    # REVIEW is a suggestion, not an automatic defect decision.
    ranked_input["suggested_action"] = "REVIEW"

    # 3. Add camera and lighting context.
    ranked_input["slice"] = (
        ranked_input["camera_id"].astype(str)
        + "/"
        + ranked_input["light"].astype(str)
    )

    # 4. Preserve the relative image path.
    ranked_input["evidence_path"] = (
        ranked_input["path"].astype(str)
    )

    # 5. Create the top-B review queue.
    q = make_review_queue(
        ranked_input,
        id_col="image_id",
        score_col="score",
        budget=budget,
        reason_col="reason",
        action_col="suggested_action",
        slice_col="slice",
        evidence_col="evidence_path",
    )

    # 6. Save structured review queue.
    queue_path = ctx.out("review_queue.csv")
    write_review_queue(q, queue_path)

    # 7. Generate offline HTML contact sheet.
    # Thumbnails are embedded, so the HTML is portable.
    contact_sheet_path = ctx.out("contact_sheet.html")

    render_contact_sheet(
        queue=q,
        out_html=contact_sheet_path,
        image_col="evidence_path",
        image_root=ctx.input_dir,
        title="T02 Raw QC - Human Review",
        embed=True,
    )

    # 8. Record pipeline statistics.
    ctx.stats["n_ranked"] = len(q)
    ctx.stats["review_budget"] = budget
    ctx.stats["contact_sheet"] = str(contact_sheet_path)

    return q


# ---------------------------------------------------------------- 04 review
def review(
    ctx: RunContext,
    scored: pd.DataFrame,
    queue: pd.DataFrame,
) -> pd.DataFrame:
    """Load reviewer decisions if an exported review CSV exists.

    Reviewer overrides are not applied yet. The decision semantics and
    audit behavior must be implemented before accepting overrides.
    """

    reviewed_path = (
        ctx.output_dir / "review_queue_reviewed.csv"
    )

    if reviewed_path.exists():
        reviewed = load_review_decisions(reviewed_path)
        ctx.stats["n_reviewed"] = len(reviewed)

        # TODO:
        # Define T02-specific decision semantics.
        # Apply valid overrides and log every change to ctx.audit.

    return scored


# ---------------------------------------------------------------- 05 decide

def decide(
    ctx: RunContext,
    final: pd.DataFrame,
) -> Decision:
    """
    T02 decision policy:
      GO     : all review-queue items approved.
      HOLD   : missing evidence, incomplete review, escalation,
               invalid provenance, or policy not configured.
      REWORK : at least one rejected item and no unresolved escalation.

    Reviewer semantics:
      approve = KEEP
      reject  = RECAPTURE
      escalate = HOLD
    """

    from .common.decision import Decision
    from .common.review import load_review_decisions

    owner = str(
        ctx.config.get("owner", "")
    ).strip()

    if not owner:
        owner = "UNASSIGNED - T02 Data Quality Owner"

    evidence = []
    metrics = {}

    def make_decision(status, code, reason, extra_evidence=None):
        paths = list(evidence)

        if extra_evidence:
            paths.extend(extra_evidence)

        return Decision(
            status=status,
            reason_code=code,
            reason=reason,
            owner=owner,
            scope=ctx.track,
            evidence=paths,
            metrics=metrics.copy(),
        )

    # -------------------------------------------------
    # 1. Validate decision policy configuration
    # -------------------------------------------------

    policy = ctx.config.get("decision_policy", {})

    if not isinstance(policy, dict):
        return make_decision(
            "HOLD",
            "INVALID_DECISION_POLICY",
            "Decision policy configuration is invalid."
        )

    if not policy.get("enabled", False):
        return make_decision(
            "HOLD",
            "POLICY_NOT_CONFIGURED",
            "Decision policy has not been explicitly enabled."
        )

    if not policy.get("approve_means_keep", False):
        return make_decision(
            "HOLD",
            "APPROVAL_SEMANTICS_UNCONFIRMED",
            "The meaning of reviewer approval has not been confirmed."
        )

    if not policy.get("reject_means_recapture", False):
        return make_decision(
            "HOLD",
            "REJECTION_SEMANTICS_UNCONFIRMED",
            "The meaning of reviewer rejection has not been confirmed."
        )

    if owner.startswith("UNASSIGNED"):
        return make_decision(
            "HOLD",
            "OWNER_NOT_ASSIGNED",
            "A responsible decision owner has not been assigned."
        )

    # -------------------------------------------------
    # 2. Validate provenance
    # -------------------------------------------------

    manifest_path = ctx.input_dir / "manifest.csv"

    if not manifest_path.exists():
        return make_decision(
            "HOLD",
            "MANIFEST_MISSING",
            "Manifest is missing; data provenance cannot be verified."
        )

    provenance_problems = verify_manifest(manifest_path)

    if provenance_problems:
        return make_decision(
            "HOLD",
            "PROVENANCE_FAILED",
            f"Manifest verification found "
            f"{len(provenance_problems)} problem(s)."
        )

    evidence.append(str(manifest_path))

    # -------------------------------------------------
    # 3. Validate final predictions
    # -------------------------------------------------

    required_columns = {"image_id", "score"}

    if not required_columns.issubset(final.columns):
        return make_decision(
            "HOLD",
            "INVALID_PREDICTIONS",
            "Final predictions are missing required columns."
        )

    if final.empty or final["image_id"].isna().any():
        return make_decision(
            "HOLD",
            "INVALID_PREDICTIONS",
            "Final predictions are empty or contain missing image IDs."
        )

    if final["image_id"].duplicated().any():
        return make_decision(
            "HOLD",
            "DUPLICATE_IMAGE_IDS",
            "Final predictions contain duplicate image IDs."
        )

    scores = pd.to_numeric(final["score"], errors="coerce")

    if scores.isna().any() or not scores.between(0, 1).all():
        return make_decision(
            "HOLD",
            "INVALID_SCORE_VALUES",
            "Prediction scores contain invalid values."
        )

    # -------------------------------------------------
    # 4. Load the current review queue
    # -------------------------------------------------

    queue_path = ctx.output_dir / "review_queue.csv"

    if not queue_path.exists():
        return make_decision(
            "HOLD",
            "REVIEW_QUEUE_MISSING",
            "Review queue was not generated."
        )

    queue = pd.read_csv(queue_path, dtype=str).fillna("")

    if "item_id" not in queue.columns or queue.empty:
        return make_decision(
            "HOLD",
            "INVALID_REVIEW_QUEUE",
            "Review queue is empty or missing item_id."
        )

    queue_ids = queue["item_id"].astype(str).tolist()

    if len(queue_ids) != len(set(queue_ids)):
        return make_decision(
            "HOLD",
            "DUPLICATE_QUEUE_ITEMS",
            "Review queue contains duplicate image IDs."
        )

    evidence.append(str(queue_path))

    # -------------------------------------------------
    # 5. Load human review decisions
    # -------------------------------------------------

    reviewed_path = (
        ctx.output_dir / "review_queue_reviewed.csv"
    )

    if not reviewed_path.exists():
        return make_decision(
            "HOLD",
            "REVIEW_NOT_COMPLETED",
            "No completed human review file was found."
        )

    try:
        reviewed = load_review_decisions(reviewed_path)

    except (ValueError, FileNotFoundError, KeyError) as exc:
        return make_decision(
            "HOLD",
            "INVALID_REVIEW_RECORD",
            f"Human review validation failed: {exc}"
        )

    evidence.append(str(reviewed_path))

    reviewed_ids = reviewed["item_id"].astype(str).tolist()

    if len(reviewed_ids) != len(set(reviewed_ids)):
        return make_decision(
            "HOLD",
            "DUPLICATE_REVIEW_RECORDS",
            "Reviewed file contains duplicate item IDs."
        )

    # Reject stale review files or decisions for another queue.
    queue_set = set(queue_ids)
    reviewed_set = set(reviewed_ids)

    if not reviewed_set.issubset(queue_set):
        return make_decision(
            "HOLD",
            "STALE_REVIEW_QUEUE",
            "Reviewed items do not belong to the current review queue."
        )

    missing_reviews = queue_set - reviewed_set

    metrics.update({
        "n_items": len(final),
        "review_budget": len(queue),
        "n_reviewed": len(reviewed),
        "n_pending": len(missing_reviews),
    })

    # Every item in the review budget must be reviewed.
    if missing_reviews:
        return make_decision(
            "HOLD",
            "REVIEW_INCOMPLETE",
            f"{len(missing_reviews)} review-queue item(s) "
            "have not been reviewed."
        )

    # -------------------------------------------------
    # 6. Aggregate reviewer decisions
    # -------------------------------------------------

    decisions = (
        reviewed["reviewer_decision"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    counts = decisions.value_counts().to_dict()

    n_approve = int(counts.get("approve", 0))
    n_reject = int(counts.get("reject", 0))
    n_escalate = int(counts.get("escalate", 0))
    n_other = len(reviewed) - n_approve - n_reject - n_escalate

    metrics.update({
        "n_approve": n_approve,
        "n_reject": n_reject,
        "n_escalate": n_escalate,
        "n_other": n_other,
    })

    # -------------------------------------------------
    # 7. HOLD: unresolved escalation or ambiguous action
    # -------------------------------------------------

    if n_escalate > 0:
        return make_decision(
            "HOLD",
            "REVIEW_ESCALATION_REQUIRED",
            f"{n_escalate} item(s) require further human review."
        )

    if n_other > 0:
        return make_decision(
            "HOLD",
            "REVIEW_ACTION_UNRESOLVED",
            f"{n_other} item(s) have unresolved reviewer actions."
        )

    # -------------------------------------------------
    # 8. REWORK: at least one rejected image
    # -------------------------------------------------

    if n_reject > 0:
        return make_decision(
            "REWORK",
            "RECAPTURE_REQUIRED",
            f"{n_reject} image(s) were rejected and require recapture."
        )

    # -------------------------------------------------
    # 9. GO: all reviewed images approved
    # -------------------------------------------------

    if n_approve == len(queue):
        return make_decision(
            "GO",
            "ALL_REVIEW_ITEMS_APPROVED",
            "All review-budget items were approved and provenance verification passed."
        )

    # -------------------------------------------------
    # 10. Fallback: never release without clear evidence
    # -------------------------------------------------

    return make_decision(
        "HOLD",
        "DECISION_UNRESOLVED",
        "Available evidence is insufficient for a release decision."
    )


# ---------------------------------------------------------------- run
def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)

    data = load(ctx)

    scored = process(ctx, data)
    ctx.stats["n_items"] = len(scored)

    queue = rank(ctx, scored)

    final = review(ctx, scored, queue)

    # Keep the official prediction columns first.
    output_columns = (
        spec.pred_columns
        + [
            column
            for column in final.columns
            if column not in spec.pred_columns
        ]
    )

    final[output_columns].to_csv(
        ctx.out(spec.pred_file),
        index=False,
    )

    write_decision(
        decide(ctx, final),
        ctx.out("decision.json"),
        ctx.out("decision_log.csv"),
    )

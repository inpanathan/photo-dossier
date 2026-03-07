"""Evaluation runner — measures retrieval precision and recall.

Compares retrieval results against ground-truth manifests to
compute per-subject and aggregate metrics.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from src.models import (
    EvaluationReport,
    SubjectEvaluation,
    SubjectManifest,
    SubjectType,
)
from src.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)


def evaluate(
    subjects: list[SubjectManifest],
    retrieval_service: RetrievalService,
    threshold: float | None = None,
    top_k: int | None = None,
) -> EvaluationReport:
    """Run evaluation for all subjects in the manifest.

    Args:
        subjects: List of ground-truth subject manifests.
        retrieval_service: Configured retrieval service instance.
        threshold: Optional similarity threshold override.
        top_k: Optional max results override.

    Returns:
        EvaluationReport with per-subject and aggregate metrics.
    """
    per_subject: list[SubjectEvaluation] = []
    cross_type_confusions = 0

    for subject in subjects:
        logger.info("evaluating_subject", subject_id=subject.subject_id, name=subject.name)

        # Run retrieval using the reference photo
        _session_id, matches = retrieval_service.query(
            image_path=subject.reference_photo,
            subject_type=subject.subject_type,
            threshold=threshold,
            top_k=top_k,
        )

        # Compare against ground truth
        ground_truth = set(subject.photos)
        retrieved = {m.image_id for m in matches}

        true_positives = len(ground_truth & retrieved)
        false_positives = len(retrieved - ground_truth)
        false_negatives = len(ground_truth - retrieved)

        precision = true_positives / max(len(retrieved), 1)
        recall = true_positives / max(len(ground_truth), 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        # Check for cross-type confusion
        for m in matches:
            if m.subject_type != subject.subject_type:
                cross_type_confusions += 1

        eval_result = SubjectEvaluation(
            subject_id=subject.subject_id,
            subject_type=subject.subject_type,
            total_ground_truth=len(ground_truth),
            retrieved_count=len(retrieved),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            false_positive_images=sorted(retrieved - ground_truth),
            false_negative_images=sorted(ground_truth - retrieved),
        )
        per_subject.append(eval_result)

        logger.info(
            "subject_evaluated",
            subject_id=subject.subject_id,
            precision=eval_result.precision,
            recall=eval_result.recall,
            f1=eval_result.f1,
        )

    # Compute aggregates
    report = _compute_aggregates(per_subject, cross_type_confusions)

    logger.info(
        "evaluation_completed",
        total_subjects=report.total_subjects,
        aggregate_precision=report.aggregate_precision,
        aggregate_recall=report.aggregate_recall,
        aggregate_f1=report.aggregate_f1,
        cross_type_confusions=cross_type_confusions,
    )

    return report


def _compute_aggregates(
    per_subject: list[SubjectEvaluation],
    cross_type_confusions: int,
) -> EvaluationReport:
    """Compute aggregate metrics from per-subject evaluations."""
    if not per_subject:
        return EvaluationReport()

    human_evals = [e for e in per_subject if e.subject_type == SubjectType.HUMAN]
    pet_evals = [e for e in per_subject if e.subject_type == SubjectType.PET]

    def _avg(evals: list[SubjectEvaluation], field: str) -> float:
        if not evals:
            return 0.0
        total: float = sum(getattr(e, field) for e in evals)
        return round(total / len(evals), 4)

    return EvaluationReport(
        total_subjects=len(per_subject),
        human_subjects=len(human_evals),
        pet_subjects=len(pet_evals),
        aggregate_precision=_avg(per_subject, "precision"),
        aggregate_recall=_avg(per_subject, "recall"),
        aggregate_f1=_avg(per_subject, "f1"),
        human_precision=_avg(human_evals, "precision"),
        human_recall=_avg(human_evals, "recall"),
        human_f1=_avg(human_evals, "f1"),
        pet_precision=_avg(pet_evals, "precision"),
        pet_recall=_avg(pet_evals, "recall"),
        pet_f1=_avg(pet_evals, "f1"),
        per_subject=per_subject,
        cross_type_confusions=cross_type_confusions,
        evaluated_at=datetime.now(tz=UTC),
    )

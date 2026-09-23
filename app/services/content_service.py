from dataclasses import dataclass, field

from app.agents.base import PostRating
from app.config import Settings


@dataclass
class ApprovalDecision:
    approved: bool
    failed_criteria: list[str] = field(default_factory=list)


def evaluate_approval(rating: PostRating, s: Settings) -> ApprovalDecision:
    """Multi-criteria gate: a high average can never hide a failing criterion."""
    failed: list[str] = []
    if rating.human_naturalness < s.rater_approval_threshold:
        failed.append(f"human_naturalness {rating.human_naturalness} < {s.rater_approval_threshold}")
    if rating.personal_voice < s.rater_min_personal_voice:
        failed.append(f"personal_voice {rating.personal_voice} < {s.rater_min_personal_voice}")
    if rating.specificity < s.rater_min_specificity:
        failed.append(f"specificity {rating.specificity} < {s.rater_min_specificity}")
    if rating.factual_confidence < s.rater_min_factual_confidence:
        failed.append(f"factual_confidence {rating.factual_confidence} < {s.rater_min_factual_confidence}")
    if rating.generic_ai_language > s.rater_max_generic_ai_language:
        failed.append(f"generic_ai_language {rating.generic_ai_language} > {s.rater_max_generic_ai_language}")
    if rating.fabricated_personal_claim_prob > s.rater_max_fabrication_prob:
        failed.append(
            f"fabricated_personal_claim_prob {rating.fabricated_personal_claim_prob:.2f} > {s.rater_max_fabrication_prob}"
        )
    return ApprovalDecision(approved=not failed, failed_criteria=failed)

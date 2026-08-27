"""JSON schemas and post-generation validation for phase-5 annotations."""

from __future__ import annotations

import re
from typing import Any

SCHEMA_VERSION = "1.0"
PROFILE_AXES = ("risk", "morality", "action")
SUPPORT_VALUES = ("clear", "mixed", "insufficient")
CHOICE_REF_PATTERN = r"^S[0-9]{3}-C[0-9]{2}$"
STORY_REF_PATTERN = r"^S[0-9]{3}(?:-C[0-9]{2})?$"
PARAGRAPH_ID_PATTERN = r"^[0-9]+$"


def text_schema(max_length: int = 1200) -> dict[str, Any]:
    """Return the common non-empty bounded justification schema."""
    return {"type": "string", "minLength": 1, "maxLength": max_length}


def ref_array_schema(pattern: str, maximum: int) -> dict[str, Any]:
    """Return a unique bounded array of reference strings."""
    return {
        "type": "array",
        "items": {"type": "string", "pattern": pattern},
        "maxItems": maximum,
        "uniqueItems": True,
    }


def axis_schema(labels: list[str]) -> dict[str, Any]:
    """Return one individual perceived-profile axis schema."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "label",
            "support",
            "justification",
            "supporting_choice_refs",
            "counterevidence_choice_refs",
        ],
        "properties": {
            "label": {"type": "string", "enum": labels},
            "support": {"type": "string", "enum": list(SUPPORT_VALUES)},
            "justification": text_schema(),
            "supporting_choice_refs": ref_array_schema(
                CHOICE_REF_PATTERN, 3
            ),
            "counterevidence_choice_refs": ref_array_schema(
                CHOICE_REF_PATTERN, 2
            ),
        },
    }


INDIVIDUAL_ANNOTATION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "phase5-individual-annotation-v1",
    "title": "Phase 5 individual trajectory annotation",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "trajectory_id",
        "perceived_profile",
        "causal_continuity",
        "profile_coherence",
    ],
    "properties": {
        "trajectory_id": {
            "type": "string",
            "pattern": r"^T[0-9]{4}$",
        },
        "perceived_profile": {
            "type": "object",
            "additionalProperties": False,
            "required": list(PROFILE_AXES),
            "properties": {
                "risk": axis_schema(
                    ["cautious", "neutral", "reckless", "unclear"]
                ),
                "morality": axis_schema(
                    ["selfish", "neutral", "noble", "unclear"]
                ),
                "action": axis_schema(
                    ["physical", "neutral", "tactical", "unclear"]
                ),
            },
        },
        "causal_continuity": {
            "type": "object",
            "additionalProperties": False,
            "required": ["label", "justification", "evidence_paragraph_ids"],
            "properties": {
                "label": {
                    "type": "string",
                    "enum": ["continuous", "minor_gap", "broken", "unclear"],
                },
                "justification": text_schema(),
                "evidence_paragraph_ids": ref_array_schema(
                    PARAGRAPH_ID_PATTERN, 4
                ),
            },
        },
        "profile_coherence": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "label",
                "justification",
                "supporting_choice_refs",
                "counterevidence_choice_refs",
            ],
            "properties": {
                "label": {
                    "type": "string",
                    "enum": [
                        "coherent",
                        "mixed",
                        "incoherent",
                        "insufficient_evidence",
                    ],
                },
                "justification": text_schema(),
                "supporting_choice_refs": ref_array_schema(
                    CHOICE_REF_PATTERN, 3
                ),
                "counterevidence_choice_refs": ref_array_schema(
                    CHOICE_REF_PATTERN, 2
                ),
            },
        },
    },
}

PAIRWISE_ANNOTATION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "phase5-pairwise-annotation-v1",
    "title": "Phase 5 pairwise trajectory annotation",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "comparison_id",
        "trajectory_a_id",
        "trajectory_b_id",
        "narrative_distinctness",
        "perceived_profile_shift",
        "profile_shift_justification",
        "evidence_story_a",
        "evidence_story_b",
    ],
    "properties": {
        "comparison_id": {
            "type": "string",
            "pattern": r"^C[0-9]{3}_(?:AB|BA)$",
        },
        "trajectory_a_id": {
            "type": "string",
            "pattern": r"^T[0-9]{4}$",
        },
        "trajectory_b_id": {
            "type": "string",
            "pattern": r"^T[0-9]{4}$",
        },
        "narrative_distinctness": {
            "type": "object",
            "additionalProperties": False,
            "required": ["label", "justification"],
            "properties": {
                "label": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "unclear"],
                },
                "justification": text_schema(),
            },
        },
        "perceived_profile_shift": {
            "type": "object",
            "additionalProperties": False,
            "required": list(PROFILE_AXES),
            "properties": {
                "risk": {
                    "type": "string",
                    "enum": [
                        "A_more_cautious",
                        "similar",
                        "A_more_reckless",
                        "unclear",
                    ],
                },
                "morality": {
                    "type": "string",
                    "enum": [
                        "A_more_selfish",
                        "similar",
                        "A_more_noble",
                        "unclear",
                    ],
                },
                "action": {
                    "type": "string",
                    "enum": [
                        "A_more_physical",
                        "similar",
                        "A_more_tactical",
                        "unclear",
                    ],
                },
            },
        },
        "profile_shift_justification": text_schema(1600),
        "evidence_story_a": ref_array_schema(STORY_REF_PATTERN, 5),
        "evidence_story_b": ref_array_schema(STORY_REF_PATTERN, 5),
    },
}


def require_object(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    """Return an object or append one validation error."""
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return {}
    return value


def require_exact_keys(
    value: dict[str, Any], expected: set[str], path: str, errors: list[str]
) -> None:
    """Require exactly the declared object keys."""
    missing = expected - set(value)
    extra = set(value) - expected
    if missing:
        errors.append(f"{path} is missing {sorted(missing)}")
    if extra:
        errors.append(f"{path} has unexpected keys {sorted(extra)}")


def require_string(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allowed: set[str] | None = None,
    pattern: str | None = None,
) -> None:
    """Require a non-empty string and optional enum/pattern constraints."""
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")
        return
    if allowed is not None and value not in allowed:
        errors.append(f"{path} has invalid value {value!r}")
    if pattern is not None and re.fullmatch(pattern, value) is None:
        errors.append(f"{path} has invalid format {value!r}")


def require_refs(
    value: Any,
    path: str,
    errors: list[str],
    *,
    pattern: str,
    maximum: int,
) -> None:
    """Require a bounded unique list of formatted references."""
    if not isinstance(value, list):
        errors.append(f"{path} must be an array")
        return
    if len(value) > maximum:
        errors.append(f"{path} contains more than {maximum} references")
    if len({str(item) for item in value}) != len(value):
        errors.append(f"{path} contains duplicate references")
    for index, item in enumerate(value):
        require_string(
            item,
            f"{path}[{index}]",
            errors,
            pattern=pattern,
        )


def validate_axis(
    value: Any, path: str, labels: set[str], errors: list[str]
) -> None:
    """Validate one perceived-profile axis object."""
    row = require_object(value, path, errors)
    fields = {
        "label",
        "support",
        "justification",
        "supporting_choice_refs",
        "counterevidence_choice_refs",
    }
    require_exact_keys(row, fields, path, errors)
    require_string(row.get("label"), f"{path}.label", errors, allowed=labels)
    require_string(
        row.get("support"),
        f"{path}.support",
        errors,
        allowed=set(SUPPORT_VALUES),
    )
    require_string(row.get("justification"), f"{path}.justification", errors)
    require_refs(
        row.get("supporting_choice_refs"),
        f"{path}.supporting_choice_refs",
        errors,
        pattern=CHOICE_REF_PATTERN,
        maximum=3,
    )
    require_refs(
        row.get("counterevidence_choice_refs"),
        f"{path}.counterevidence_choice_refs",
        errors,
        pattern=CHOICE_REF_PATTERN,
        maximum=2,
    )


def validate_individual_annotation(value: Any) -> list[str]:
    """Validate one generated individual annotation structurally."""
    errors: list[str] = []
    row = require_object(value, "$", errors)
    fields = {
        "trajectory_id",
        "perceived_profile",
        "causal_continuity",
        "profile_coherence",
    }
    require_exact_keys(row, fields, "$", errors)
    require_string(
        row.get("trajectory_id"),
        "$.trajectory_id",
        errors,
        pattern=r"^T[0-9]{4}$",
    )
    profile = require_object(
        row.get("perceived_profile"), "$.perceived_profile", errors
    )
    require_exact_keys(profile, set(PROFILE_AXES), "$.perceived_profile", errors)
    validate_axis(
        profile.get("risk"),
        "$.perceived_profile.risk",
        {"cautious", "neutral", "reckless", "unclear"},
        errors,
    )
    validate_axis(
        profile.get("morality"),
        "$.perceived_profile.morality",
        {"selfish", "neutral", "noble", "unclear"},
        errors,
    )
    validate_axis(
        profile.get("action"),
        "$.perceived_profile.action",
        {"physical", "neutral", "tactical", "unclear"},
        errors,
    )
    continuity = require_object(
        row.get("causal_continuity"), "$.causal_continuity", errors
    )
    require_exact_keys(
        continuity,
        {"label", "justification", "evidence_paragraph_ids"},
        "$.causal_continuity",
        errors,
    )
    require_string(
        continuity.get("label"),
        "$.causal_continuity.label",
        errors,
        allowed={"continuous", "minor_gap", "broken", "unclear"},
    )
    require_string(
        continuity.get("justification"),
        "$.causal_continuity.justification",
        errors,
    )
    require_refs(
        continuity.get("evidence_paragraph_ids"),
        "$.causal_continuity.evidence_paragraph_ids",
        errors,
        pattern=PARAGRAPH_ID_PATTERN,
        maximum=4,
    )
    evidence = continuity.get("evidence_paragraph_ids")
    if continuity.get("label") in {"minor_gap", "broken"} and (
        not isinstance(evidence, list) or len(evidence) < 2
    ):
        errors.append("causal gaps require at least two paragraph identifiers")
    coherence = require_object(
        row.get("profile_coherence"), "$.profile_coherence", errors
    )
    require_exact_keys(
        coherence,
        {
            "label",
            "justification",
            "supporting_choice_refs",
            "counterevidence_choice_refs",
        },
        "$.profile_coherence",
        errors,
    )
    require_string(
        coherence.get("label"),
        "$.profile_coherence.label",
        errors,
        allowed={"coherent", "mixed", "incoherent", "insufficient_evidence"},
    )
    require_string(
        coherence.get("justification"),
        "$.profile_coherence.justification",
        errors,
    )
    require_refs(
        coherence.get("supporting_choice_refs"),
        "$.profile_coherence.supporting_choice_refs",
        errors,
        pattern=CHOICE_REF_PATTERN,
        maximum=3,
    )
    require_refs(
        coherence.get("counterevidence_choice_refs"),
        "$.profile_coherence.counterevidence_choice_refs",
        errors,
        pattern=CHOICE_REF_PATTERN,
        maximum=2,
    )
    return errors


def validate_pairwise_annotation(value: Any) -> list[str]:
    """Validate one generated pairwise annotation structurally."""
    errors: list[str] = []
    row = require_object(value, "$", errors)
    fields = {
        "comparison_id",
        "trajectory_a_id",
        "trajectory_b_id",
        "narrative_distinctness",
        "perceived_profile_shift",
        "profile_shift_justification",
        "evidence_story_a",
        "evidence_story_b",
    }
    require_exact_keys(row, fields, "$", errors)
    require_string(
        row.get("comparison_id"),
        "$.comparison_id",
        errors,
        pattern=r"^C[0-9]{3}_(?:AB|BA)$",
    )
    for field in ("trajectory_a_id", "trajectory_b_id"):
        require_string(
            row.get(field),
            f"$.{field}",
            errors,
            pattern=r"^T[0-9]{4}$",
        )
    distinctness = require_object(
        row.get("narrative_distinctness"), "$.narrative_distinctness", errors
    )
    require_exact_keys(
        distinctness,
        {"label", "justification"},
        "$.narrative_distinctness",
        errors,
    )
    require_string(
        distinctness.get("label"),
        "$.narrative_distinctness.label",
        errors,
        allowed={"low", "medium", "high", "unclear"},
    )
    require_string(
        distinctness.get("justification"),
        "$.narrative_distinctness.justification",
        errors,
    )
    shifts = require_object(
        row.get("perceived_profile_shift"), "$.perceived_profile_shift", errors
    )
    require_exact_keys(shifts, set(PROFILE_AXES), "$.perceived_profile_shift", errors)
    allowed_shifts = {
        "risk": {"A_more_cautious", "similar", "A_more_reckless", "unclear"},
        "morality": {"A_more_selfish", "similar", "A_more_noble", "unclear"},
        "action": {"A_more_physical", "similar", "A_more_tactical", "unclear"},
    }
    for axis, allowed in allowed_shifts.items():
        require_string(
            shifts.get(axis),
            f"$.perceived_profile_shift.{axis}",
            errors,
            allowed=allowed,
        )
    require_string(
        row.get("profile_shift_justification"),
        "$.profile_shift_justification",
        errors,
    )
    require_refs(
        row.get("evidence_story_a"),
        "$.evidence_story_a",
        errors,
        pattern=STORY_REF_PATTERN,
        maximum=5,
    )
    require_refs(
        row.get("evidence_story_b"),
        "$.evidence_story_b",
        errors,
        pattern=STORY_REF_PATTERN,
        maximum=5,
    )
    return errors

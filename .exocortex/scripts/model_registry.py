#!/usr/bin/env python3
"""Validate model evidence and compare official observations without mutation.

The utility is deliberately offline. Source acquisition is a separately
authorized read-only activity that produces a normalized observation JSON.
This program validates that evidence, proposes quarantine for unknown models,
and never admits a model to routing or edits repository state.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, Optional, Sequence
from urllib.parse import urlsplit


SCHEMA_VERSION = "public-v2"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
RISKS = ("low", "medium", "high", "critical")
LIFECYCLES = ("active", "preview", "deprecated", "retired", "unknown")
ROUTING_STATUSES = ("candidate", "eligible", "quarantined", "deprecated")
PROFILE_STATUSES = ("candidate", "verified", "failed")
MAX_AVAILABILITY_WINDOW = timedelta(minutes=15)
SOURCE_ROLES = ("models", "pricing", "lifecycle", "availability")
OBSERVED_FACT_ROLES = {
    "display_name": "models",
    "lifecycle": "lifecycle",
    "input_microusd_per_mtok": "pricing",
    "output_microusd_per_mtok": "pricing",
}
TRUSTED_OFFICIAL_HOSTS = frozenset(
    {
        "ai.google.dev",
        "api-docs.deepseek.com",
        "developers.openai.com",
        "docs.mistral.ai",
        "docs.x.ai",
        "platform.claude.com",
        "platform.kimi.ai",
    }
)


class RegistryError(RuntimeError):
    """Stable, non-sensitive model-registry validation error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RegistryError("duplicate_json_key", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RegistryError("invalid_json", f"invalid JSON document: {path.name}") from exc
    if not isinstance(value, dict):
        raise RegistryError("invalid_json_root", f"JSON root must be an object: {path.name}")
    return value


def exact_keys(value: Dict[str, Any], required: Iterable[str], optional: Iterable[str], label: str) -> None:
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    extra = sorted(set(value) - allowed)
    if missing:
        raise RegistryError("missing_field", f"{label} is missing field: {missing[0]}")
    if extra:
        raise RegistryError("unexpected_field", f"{label} contains unexpected field: {extra[0]}")


def require_id(value: object, label: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise RegistryError("invalid_id", f"{label} must be a lowercase stable identifier")
    return value


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise RegistryError("invalid_sha256", f"{label} must be a lowercase SHA-256 digest")
    return value


def parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RegistryError("invalid_timestamp", f"{label} must be a UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RegistryError("invalid_timestamp", f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RegistryError("invalid_timestamp", f"{label} must be UTC")
    return parsed


def require_unique_strings(value: object, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RegistryError("invalid_array", f"{label} must contain non-empty strings")
    if not allow_empty and not value:
        raise RegistryError("invalid_array", f"{label} must not be empty")
    if len(value) != len(set(value)):
        raise RegistryError("duplicate_value", f"{label} contains duplicate values")
    return value


def require_nonnegative_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RegistryError("invalid_integer", f"{label} must be a non-negative integer")
    return value


def validate_official_url(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) > 500:
        raise RegistryError("invalid_source_url", f"{label} must be an HTTPS official source URL")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in TRUSTED_OFFICIAL_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RegistryError("untrusted_source_url", f"{label} is not an approved credential-free official source")
    return value


def validate_source_registry(document: Dict[str, Any]) -> Dict[str, Any]:
    exact_keys(
        document,
        ("schema_version", "kind", "registry_version", "observed_at", "expires_at", "sources"),
        (),
        "source registry",
    )
    if document["schema_version"] != SCHEMA_VERSION or document["kind"] != "model_source_registry":
        raise RegistryError("wrong_schema", "source registry must use public-v2 model_source_registry")
    version = document["registry_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise RegistryError("invalid_registry_version", "registry_version must be a positive integer")
    observed_at = parse_timestamp(document["observed_at"], "source registry observed_at")
    expires_at = parse_timestamp(document["expires_at"], "source registry expires_at")
    if expires_at <= observed_at:
        raise RegistryError("invalid_freshness_window", "source registry expires_at must follow observed_at")
    if not isinstance(document["sources"], list) or not document["sources"]:
        raise RegistryError("invalid_sources", "source registry must contain at least one source")

    source_ids: set[str] = set()
    source_urls: set[str] = set()
    for item in document["sources"]:
        if not isinstance(item, dict):
            raise RegistryError("invalid_source", "source entries must be objects")
        exact_keys(
            item,
            (
                "id",
                "provider_id",
                "url",
                "roles",
                "retrieved_at",
                "content_sha256",
                "refresh_interval_hours",
            ),
            (),
            "source entry",
        )
        source_id = require_id(item["id"], "source id")
        require_id(item["provider_id"], "source provider_id")
        url = validate_official_url(item["url"], "source url")
        roles = require_unique_strings(item["roles"], "source roles", allow_empty=False)
        if any(role not in SOURCE_ROLES for role in roles):
            raise RegistryError("invalid_source_role", "source roles contain an unsupported role")
        retrieved_at = parse_timestamp(item["retrieved_at"], "source retrieved_at")
        if retrieved_at > observed_at:
            raise RegistryError("future_source_evidence", "source retrieved_at cannot follow registry observed_at")
        require_sha256(item["content_sha256"], "source content_sha256")
        refresh = item["refresh_interval_hours"]
        if not isinstance(refresh, int) or isinstance(refresh, bool) or not 1 <= refresh <= 720:
            raise RegistryError("invalid_refresh_interval", "source refresh_interval_hours must be 1 through 720")
        if source_id in source_ids or url in source_urls:
            raise RegistryError("duplicate_source", "source ids and URLs must be unique")
        source_ids.add(source_id)
        source_urls.add(url)
    return document


def validate_candidate_source_registry(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate a refreshed acquisition snapshot without rebinding the catalog."""

    baseline = validate_source_registry(baseline)
    candidate = validate_source_registry(candidate)
    if candidate["registry_version"] < baseline["registry_version"]:
        raise RegistryError("source_snapshot_regression", "candidate source registry version regressed")
    if parse_timestamp(candidate["observed_at"], "candidate source registry observed_at") < parse_timestamp(
        baseline["observed_at"],
        "baseline source registry observed_at",
    ):
        raise RegistryError("source_snapshot_regression", "candidate source registry observed_at regressed")
    if parse_timestamp(candidate["expires_at"], "candidate source registry expires_at") < parse_timestamp(
        baseline["expires_at"],
        "baseline source registry expires_at",
    ):
        raise RegistryError("source_snapshot_regression", "candidate source registry expires_at regressed")

    baseline_by_id = {source["id"]: source for source in baseline["sources"]}
    candidate_by_id = {source["id"]: source for source in candidate["sources"]}
    if set(candidate_by_id) != set(baseline_by_id):
        raise RegistryError(
            "source_definition_mismatch",
            "candidate source registry must contain the exact baseline source IDs",
        )
    definition_fields = ("id", "provider_id", "url", "roles", "refresh_interval_hours")
    for source_id in sorted(baseline_by_id):
        baseline_source = baseline_by_id[source_id]
        candidate_source = candidate_by_id[source_id]
        baseline_definition = {
            field: sorted(baseline_source[field]) if field == "roles" else baseline_source[field]
            for field in definition_fields
        }
        candidate_definition = {
            field: sorted(candidate_source[field]) if field == "roles" else candidate_source[field]
            for field in definition_fields
        }
        if candidate_definition != baseline_definition:
            raise RegistryError(
                "source_definition_mismatch",
                f"candidate source definition changed: {source_id}",
            )
        baseline_retrieved = parse_timestamp(baseline_source["retrieved_at"], "baseline source retrieved_at")
        candidate_retrieved = parse_timestamp(candidate_source["retrieved_at"], "candidate source retrieved_at")
        if candidate_retrieved < baseline_retrieved:
            raise RegistryError(
                "source_snapshot_regression",
                f"candidate source retrieval regressed: {source_id}",
            )
        if (
            candidate_retrieved == baseline_retrieved
            and candidate_source["content_sha256"] != baseline_source["content_sha256"]
        ):
            raise RegistryError(
                "source_snapshot_mismatch",
                f"candidate source bytes changed without a new retrieval: {source_id}",
            )
    return candidate


def validate_profile(profile: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    exact_keys(
        profile,
        (
            "id",
            "status",
            "attempts",
            "successes",
            "total_cost_microusd",
            "evidence_sha256",
            "evaluated_at",
            "expires_at",
        ),
        (),
        f"evaluation profile for {model_id}",
    )
    require_id(profile["id"], "evaluation profile id")
    if profile["status"] not in PROFILE_STATUSES:
        raise RegistryError("invalid_profile_status", f"evaluation profile status is invalid: {model_id}")
    attempts = require_nonnegative_integer(profile["attempts"], "evaluation attempts")
    successes = require_nonnegative_integer(profile["successes"], "evaluation successes")
    require_nonnegative_integer(profile["total_cost_microusd"], "evaluation total_cost_microusd")
    if successes > attempts:
        raise RegistryError("invalid_success_count", f"evaluation successes exceed attempts: {model_id}")
    require_sha256(profile["evidence_sha256"], "evaluation evidence_sha256")
    evaluated_at = parse_timestamp(profile["evaluated_at"], "evaluation evaluated_at")
    expires_at = parse_timestamp(profile["expires_at"], "evaluation expires_at")
    if expires_at <= evaluated_at:
        raise RegistryError("invalid_profile_window", f"evaluation expiry must follow evaluation: {model_id}")
    if profile["status"] == "verified" and (attempts == 0 or successes == 0):
        raise RegistryError("unproven_profile", f"verified evaluation requires at least one success: {model_id}")
    return profile


def validate_catalog(document: Dict[str, Any], source_registry: Dict[str, Any]) -> Dict[str, Any]:
    source_registry = validate_source_registry(source_registry)
    exact_keys(
        document,
        (
            "schema_version",
            "kind",
            "catalog_version",
            "source_registry_digest",
            "observed_at",
            "expires_at",
            "models",
        ),
        (),
        "routing catalog",
    )
    if document["schema_version"] != SCHEMA_VERSION or document["kind"] != "model_routing_catalog":
        raise RegistryError("wrong_schema", "routing catalog must use public-v2 model_routing_catalog")
    version = document["catalog_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise RegistryError("invalid_catalog_version", "catalog_version must be a positive integer")
    expected_source_digest = canonical_digest(source_registry)
    if document["source_registry_digest"] != expected_source_digest:
        raise RegistryError("source_registry_digest_mismatch", "catalog is not bound to the supplied source registry")
    observed_at = parse_timestamp(document["observed_at"], "routing catalog observed_at")
    expires_at = parse_timestamp(document["expires_at"], "routing catalog expires_at")
    if expires_at <= observed_at:
        raise RegistryError("invalid_freshness_window", "catalog expires_at must follow observed_at")
    if not isinstance(document["models"], list):
        raise RegistryError("invalid_models", "catalog models must be an array")

    source_by_id = {item["id"]: item for item in source_registry["sources"]}
    model_ids: set[str] = set()
    for model in document["models"]:
        if not isinstance(model, dict):
            raise RegistryError("invalid_model", "catalog model entries must be objects")
        exact_keys(
            model,
            (
                "id",
                "provider_id",
                "display_name",
                "lifecycle",
                "routing_status",
                "source_ids",
                "input_microusd_per_mtok",
                "output_microusd_per_mtok",
                "capabilities",
                "max_risk",
                "parent_capable",
                "evaluation_profiles",
            ),
            (),
            "catalog model",
        )
        model_id = require_id(model["id"], "model id")
        provider_id = require_id(model["provider_id"], "model provider_id")
        if model_id in model_ids:
            raise RegistryError("duplicate_model", f"duplicate catalog model: {model_id}")
        model_ids.add(model_id)
        if not isinstance(model["display_name"], str) or not 1 <= len(model["display_name"]) <= 160:
            raise RegistryError("invalid_display_name", f"model display_name is invalid: {model_id}")
        if model["lifecycle"] not in LIFECYCLES:
            raise RegistryError("invalid_model_lifecycle", f"model lifecycle is invalid: {model_id}")
        if model["routing_status"] not in ROUTING_STATUSES:
            raise RegistryError("invalid_routing_status", f"model routing_status is invalid: {model_id}")
        source_ids = require_unique_strings(model["source_ids"], "model source_ids", allow_empty=False)
        referenced_sources = []
        for source_id in source_ids:
            require_id(source_id, "model source id")
            source = source_by_id.get(source_id)
            if source is None or source["provider_id"] != provider_id:
                raise RegistryError("invalid_model_source", f"model source does not match provider: {model_id}")
            referenced_sources.append(source)
        source_roles = {
            role
            for source in referenced_sources
            for role in source["roles"]
        }
        if "models" not in source_roles:
            raise RegistryError("missing_model_source", f"model lacks an official listing source: {model_id}")
        if model["lifecycle"] != "unknown" and "lifecycle" not in source_roles:
            raise RegistryError("missing_lifecycle_source", f"model lifecycle lacks an official source: {model_id}")
        for price_name in ("input_microusd_per_mtok", "output_microusd_per_mtok"):
            price = model[price_name]
            if price is not None:
                require_nonnegative_integer(price, f"{model_id} {price_name}")
        if (
            model["input_microusd_per_mtok"] is not None
            or model["output_microusd_per_mtok"] is not None
        ) and "pricing" not in source_roles:
            raise RegistryError("missing_pricing_source", f"model pricing lacks an official source: {model_id}")
        capabilities = require_unique_strings(model["capabilities"], "model capabilities")
        for capability in capabilities:
            require_id(capability, "model capability")
        if model["max_risk"] not in RISKS:
            raise RegistryError("invalid_model_risk", f"model max_risk is invalid: {model_id}")
        if not isinstance(model["parent_capable"], bool):
            raise RegistryError("invalid_parent_capable", f"model parent_capable must be boolean: {model_id}")
        profiles = model["evaluation_profiles"]
        if not isinstance(profiles, list):
            raise RegistryError("invalid_profiles", f"evaluation_profiles must be an array: {model_id}")
        profile_ids: set[str] = set()
        for profile in profiles:
            if not isinstance(profile, dict):
                raise RegistryError("invalid_profile", f"evaluation profiles must be objects: {model_id}")
            validate_profile(profile, model_id)
            if profile["id"] in profile_ids:
                raise RegistryError("duplicate_profile", f"duplicate evaluation profile: {model_id}/{profile['id']}")
            profile_ids.add(profile["id"])
        if model["routing_status"] == "eligible":
            if model["lifecycle"] != "active":
                raise RegistryError("ineligible_lifecycle", f"eligible model must be active: {model_id}")
            if not any(profile["status"] == "verified" for profile in profiles):
                raise RegistryError("missing_verified_profile", f"eligible model lacks verified evaluation: {model_id}")
        if model["lifecycle"] in {"deprecated", "retired"} and model["routing_status"] != "deprecated":
            raise RegistryError("unsafe_lifecycle_status", f"deprecated or retired model must be routing-deprecated: {model_id}")
    return document


def validate_availability(document: Dict[str, Any]) -> Dict[str, Any]:
    exact_keys(
        document,
        (
            "schema_version",
            "kind",
            "catalog_digest",
            "surface_id",
            "surface_version",
            "surface_session_id",
            "scope",
            "observed_at",
            "expires_at",
            "evidence_sha256",
            "model_ids",
        ),
        (),
        "availability evidence",
    )
    if document["schema_version"] != SCHEMA_VERSION or document["kind"] != "model_availability":
        raise RegistryError("wrong_schema", "availability must use public-v2 model_availability")
    require_sha256(document["catalog_digest"], "availability catalog_digest")
    require_id(document["surface_id"], "availability surface_id")
    require_id(document["surface_version"], "availability surface_version")
    require_id(document["surface_session_id"], "availability surface_session_id")
    if document["scope"] != "current_surface_session":
        raise RegistryError("invalid_availability_scope", "availability scope must be current_surface_session")
    observed_at = parse_timestamp(document["observed_at"], "availability observed_at")
    expires_at = parse_timestamp(document["expires_at"], "availability expires_at")
    if expires_at <= observed_at:
        raise RegistryError("invalid_freshness_window", "availability expires_at must follow observed_at")
    if expires_at - observed_at > MAX_AVAILABILITY_WINDOW:
        raise RegistryError(
            "invalid_freshness_window",
            "availability evidence must expire within 15 minutes of observation",
        )
    require_sha256(document["evidence_sha256"], "availability evidence_sha256")
    model_ids = require_unique_strings(document["model_ids"], "availability model_ids")
    for model_id in model_ids:
        require_id(model_id, "availability model id")
    return document


def validate_observation(document: Dict[str, Any], source_registry: Dict[str, Any]) -> Dict[str, Any]:
    source_registry = validate_source_registry(source_registry)
    exact_keys(
        document,
        ("schema_version", "kind", "observed_at", "source_registry_digest", "source_observations"),
        (),
        "model observation",
    )
    if document["schema_version"] != SCHEMA_VERSION or document["kind"] != "model_observation":
        raise RegistryError("wrong_schema", "observation must use public-v2 model_observation")
    observed_at = parse_timestamp(document["observed_at"], "observation observed_at")
    if document["source_registry_digest"] != canonical_digest(source_registry):
        raise RegistryError("source_registry_digest_mismatch", "observation is not bound to the supplied source registry")
    source_by_id = {item["id"]: item for item in source_registry["sources"]}
    if not isinstance(document["source_observations"], list) or not document["source_observations"]:
        raise RegistryError("invalid_observation", "source_observations must not be empty")
    seen_sources: set[str] = set()
    merged_models: Dict[str, tuple[object, ...]] = {}
    for source_observation in document["source_observations"]:
        if not isinstance(source_observation, dict):
            raise RegistryError("invalid_observation", "source observation entries must be objects")
        exact_keys(
            source_observation,
            (
                "source_id",
                "scope",
                "complete_listing",
                "retrieved_at",
                "content_sha256",
                "models",
            ),
            (),
            "source observation",
        )
        source_id = require_id(source_observation["source_id"], "observation source_id")
        source = source_by_id.get(source_id)
        if source is None:
            raise RegistryError("unknown_source", f"observation references unknown source: {source_id}")
        if source_id in seen_sources:
            raise RegistryError("duplicate_source_observation", f"duplicate source observation: {source_id}")
        seen_sources.add(source_id)
        if source_observation["scope"] != "registered_source":
            raise RegistryError("invalid_observation_scope", "observation scope must be registered_source")
        if not isinstance(source_observation["complete_listing"], bool):
            raise RegistryError("invalid_observation_completeness", "complete_listing must be boolean")
        if source_observation["complete_listing"] and "models" not in source["roles"]:
            raise RegistryError(
                "unauthorized_observation_completeness",
                f"complete listing requires a models source: {source_id}",
            )
        retrieved_at = parse_timestamp(source_observation["retrieved_at"], "observation retrieved_at")
        if retrieved_at > observed_at:
            raise RegistryError("future_source_evidence", "observation retrieved_at cannot follow observed_at")
        content_sha256 = require_sha256(
            source_observation["content_sha256"],
            "observation content_sha256",
        )
        if retrieved_at != parse_timestamp(source["retrieved_at"], "source retrieved_at"):
            raise RegistryError(
                "source_retrieval_mismatch",
                f"observation retrieval does not match registered source: {source_id}",
            )
        if content_sha256 != source["content_sha256"]:
            raise RegistryError(
                "source_content_mismatch",
                f"observation content does not match registered source: {source_id}",
            )
        if not isinstance(source_observation["models"], list):
            raise RegistryError("invalid_observation_models", "observation models must be an array")
        seen_models: set[str] = set()
        for model in source_observation["models"]:
            if not isinstance(model, dict):
                raise RegistryError("invalid_observed_model", "observed models must be objects")
            exact_keys(
                model,
                (
                    "id",
                    "provider_id",
                ),
                OBSERVED_FACT_ROLES,
                "observed model",
            )
            model_id = require_id(model["id"], "observed model id")
            provider_id = require_id(model["provider_id"], "observed model provider_id")
            if provider_id != source["provider_id"]:
                raise RegistryError("provider_source_mismatch", f"observed model provider does not match source: {model_id}")
            if model_id in seen_models:
                raise RegistryError("duplicate_observed_model", f"duplicate model in source observation: {model_id}")
            seen_models.add(model_id)
            present_facts = [field for field in OBSERVED_FACT_ROLES if field in model]
            if not present_facts:
                raise RegistryError(
                    "missing_observation_fact",
                    f"observed model must contain at least one source-authorized fact: {model_id}",
                )
            for field in present_facts:
                required_role = OBSERVED_FACT_ROLES[field]
                if required_role not in source["roles"]:
                    raise RegistryError(
                        "unauthorized_observation_field",
                        f"source role cannot claim {field}: {source_id}",
                    )
            if "display_name" in model and (
                not isinstance(model["display_name"], str)
                or not 1 <= len(model["display_name"]) <= 160
            ):
                raise RegistryError("invalid_display_name", f"observed model display_name is invalid: {model_id}")
            if "lifecycle" in model and model["lifecycle"] not in LIFECYCLES:
                raise RegistryError("invalid_model_lifecycle", f"observed model lifecycle is invalid: {model_id}")
            for price_name in ("input_microusd_per_mtok", "output_microusd_per_mtok"):
                if price_name not in model:
                    continue
                price = model[price_name]
                if price is not None:
                    require_nonnegative_integer(price, f"{model_id} {price_name}")
            model_facts = merged_models.setdefault(model_id, (provider_id, {}))
            if model_facts[0] != provider_id:
                raise RegistryError("conflicting_observation", f"official observations conflict for model: {model_id}")
            merged_fact_values = model_facts[1]
            if not isinstance(merged_fact_values, dict):
                raise RegistryError("invalid_observation", "internal observation merge state is invalid")
            for field in present_facts:
                if field in merged_fact_values and merged_fact_values[field] != model[field]:
                    raise RegistryError(
                        "conflicting_observation",
                        f"official observations conflict for model: {model_id}",
                    )
                merged_fact_values[field] = model[field]
    return document


def require_fresh(document: Dict[str, Any], as_of: datetime, label: str) -> None:
    observed_at = parse_timestamp(document["observed_at"], f"{label} observed_at")
    expires_at = parse_timestamp(document["expires_at"], f"{label} expires_at")
    if as_of < observed_at:
        raise RegistryError("evidence_not_yet_valid", f"{label} was observed after the routing timestamp")
    if as_of >= expires_at:
        raise RegistryError("stale_model_evidence", f"{label} expired before the routing timestamp")


def source_is_fresh(source: Dict[str, Any], as_of: datetime) -> bool:
    retrieved_at = parse_timestamp(source["retrieved_at"], "source retrieved_at")
    due_at = retrieved_at.timestamp() + (source["refresh_interval_hours"] * 3600)
    return retrieved_at <= as_of and as_of.timestamp() < due_at


def require_source_fresh(source: Dict[str, Any], as_of: datetime) -> None:
    if not source_is_fresh(source, as_of):
        raise RegistryError(
            "stale_source_evidence",
            f"official source is not fresh at the requested timestamp: {source['id']}",
        )


def parse_as_of(value: object) -> datetime:
    return parse_timestamp(value, "as_of")


def plan_refresh(
    source_registry: Dict[str, Any],
    catalog: Dict[str, Any],
    *,
    as_of: datetime,
) -> Dict[str, Any]:
    source_registry = validate_source_registry(source_registry)
    catalog = validate_catalog(catalog, source_registry)
    due_sources = []
    for source in source_registry["sources"]:
        retrieved_at = parse_timestamp(source["retrieved_at"], "source retrieved_at")
        due_at = retrieved_at.timestamp() + (source["refresh_interval_hours"] * 3600)
        if as_of.timestamp() >= due_at:
            due_sources.append(
                {
                    "source_id": source["id"],
                    "provider_id": source["provider_id"],
                    "official_url": source["url"],
                    "reason": "refresh_interval_elapsed",
                }
            )
    return {
        "ok": True,
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "coverage": "configured_official_sources_only",
        "source_registry_digest": canonical_digest(source_registry),
        "catalog_digest": canonical_digest(catalog),
        "source_registry_expired": as_of >= parse_timestamp(source_registry["expires_at"], "source registry expires_at"),
        "catalog_expired": as_of >= parse_timestamp(catalog["expires_at"], "catalog expires_at"),
        "due_sources": due_sources,
        "acquisition": "explicit_external_read",
        "credential_policy": "forbidden",
        "network_used": False,
        "mutation_performed": False,
    }


def reconcile_observations(
    source_registry: Dict[str, Any],
    observations: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Merge role-authorized facts once across the full discovery invocation."""

    source_registry = validate_source_registry(source_registry)
    source_by_id = {source["id"]: source for source in source_registry["sources"]}
    seen_sources: set[str] = set()
    models: Dict[str, Dict[str, Any]] = {}
    complete_sources: Dict[str, set[str]] = {}
    observation_digests = []
    for observation in observations:
        validated = validate_observation(observation, source_registry)
        observation_digests.append(canonical_digest(validated))
        for source_observation in validated["source_observations"]:
            source_id = source_observation["source_id"]
            if source_id in seen_sources:
                raise RegistryError(
                    "duplicate_source_observation",
                    f"source appears more than once in discovery: {source_id}",
                )
            seen_sources.add(source_id)
            source = source_by_id[source_id]
            source_model_ids: set[str] = set()
            for observed in source_observation["models"]:
                model_id = observed["id"]
                source_model_ids.add(model_id)
                merged = models.setdefault(
                    model_id,
                    {
                        "provider_id": observed["provider_id"],
                        "facts": {},
                        "source_ids": set(),
                        "listing_source_ids": set(),
                    },
                )
                if merged["provider_id"] != observed["provider_id"]:
                    raise RegistryError(
                        "conflicting_observation",
                        f"official observations conflict for model: {model_id}",
                    )
                merged["source_ids"].add(source_id)
                if "models" in source["roles"]:
                    merged["listing_source_ids"].add(source_id)
                for field in OBSERVED_FACT_ROLES:
                    if field not in observed:
                        continue
                    if field in merged["facts"] and merged["facts"][field] != observed[field]:
                        raise RegistryError(
                            "conflicting_observation",
                            f"official observations conflict for model: {model_id}",
                        )
                    merged["facts"][field] = observed[field]
            if source_observation["complete_listing"]:
                complete_sources[source_id] = source_model_ids
    return {
        "models": models,
        "complete_sources": complete_sources,
        "observation_digests": sorted(observation_digests),
    }


def compare_observations(
    baseline_source_registry: Dict[str, Any],
    catalog: Dict[str, Any],
    candidate_source_registry: Dict[str, Any],
    observations: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    baseline_source_registry = validate_source_registry(baseline_source_registry)
    catalog = validate_catalog(catalog, baseline_source_registry)
    candidate_source_registry = validate_candidate_source_registry(
        baseline_source_registry,
        candidate_source_registry,
    )
    reconciled = reconcile_observations(candidate_source_registry, observations)
    catalog_by_id = {model["id"]: model for model in catalog["models"]}

    quarantine = []
    changes = []
    for model_id, observed in sorted(reconciled["models"].items()):
        current = catalog_by_id.get(model_id)
        facts = observed["facts"]
        if current is None:
            if not observed["listing_source_ids"]:
                raise RegistryError(
                    "missing_model_listing",
                    f"new model facts lack an official models-source listing: {model_id}",
                )
            quarantine.append(
                {
                    "id": model_id,
                    "provider_id": observed["provider_id"],
                    "display_name": facts.get("display_name"),
                    "lifecycle": facts.get("lifecycle", "unknown"),
                    "routing_status": "quarantined",
                    "source_ids": sorted(observed["source_ids"]),
                    "input_microusd_per_mtok": facts.get("input_microusd_per_mtok"),
                    "output_microusd_per_mtok": facts.get("output_microusd_per_mtok"),
                    "observed_fields": sorted(facts),
                    "reason": "unreviewed_new_model",
                }
            )
            continue
        if observed["provider_id"] != current["provider_id"]:
            raise RegistryError(
                "provider_source_mismatch",
                f"observed model provider does not match catalog: {model_id}",
            )
        differing = {}
        for field, observed_value in sorted(facts.items()):
            if current[field] != observed_value:
                differing[field] = {"catalog": current[field], "observed": observed_value}
        if differing:
            changes.append({"id": model_id, "changes": differing, "routing_change_permitted": False})

    not_observed: set[str] = set()
    for source_id, observed_ids in reconciled["complete_sources"].items():
        source_catalog_ids = {
            model["id"]
            for model in catalog["models"]
            if source_id in model["source_ids"]
        }
        not_observed.update(source_catalog_ids - observed_ids)
    return {
        "ok": True,
        "policy": "compare_only_fail_closed",
        "baseline_source_registry_digest": canonical_digest(baseline_source_registry),
        "candidate_source_registry_digest": canonical_digest(candidate_source_registry),
        "source_registry_digest": canonical_digest(candidate_source_registry),
        "catalog_digest": canonical_digest(catalog),
        "observation_digests": reconciled["observation_digests"],
        "quarantine_proposals": quarantine,
        "catalog_changes": changes,
        "not_observed": sorted(not_observed),
        "missing_means_deprecated": False,
        "mutation_permitted": False,
        "activation_requires": "separately_approved_guarded_catalog_edit_and_verified_evaluation",
    }


def compare_observation(
    source_registry: Dict[str, Any],
    catalog: Dict[str, Any],
    observation: Dict[str, Any],
) -> Dict[str, Any]:
    result = compare_observations(source_registry, catalog, source_registry, [observation])
    result["observation_digest"] = result["observation_digests"][0]
    return result


def discover_models(
    baseline_source_registry: Dict[str, Any],
    catalog: Dict[str, Any],
    candidate_source_registry: Dict[str, Any],
    observations: Sequence[Dict[str, Any]],
    *,
    as_of: datetime,
) -> Dict[str, Any]:
    baseline_source_registry = validate_source_registry(baseline_source_registry)
    catalog = validate_catalog(catalog, baseline_source_registry)
    candidate_source_registry = validate_candidate_source_registry(
        baseline_source_registry,
        candidate_source_registry,
    )
    if not observations:
        raise RegistryError("missing_observation", "discovery requires at least one normalized observation")
    require_fresh(candidate_source_registry, as_of, "candidate source registry")
    source_by_id = {source["id"]: source for source in candidate_source_registry["sources"]}
    validated_observations = []
    for observation in observations:
        validated = validate_observation(observation, candidate_source_registry)
        observed_at = parse_timestamp(validated["observed_at"], "observation observed_at")
        if observed_at > as_of:
            raise RegistryError("evidence_not_yet_valid", "observation was recorded after as_of")
        for source_observation in validated["source_observations"]:
            require_source_fresh(source_by_id[source_observation["source_id"]], as_of)
        validated_observations.append(validated)
    result = compare_observations(
        baseline_source_registry,
        catalog,
        candidate_source_registry,
        validated_observations,
    )
    findings = []
    for proposal in result["quarantine_proposals"]:
        findings.append({"code": "new_model", "model_id": proposal["id"]})
    for change in result["catalog_changes"]:
        codes = set()
        if "lifecycle" in change["changes"]:
            codes.add("lifecycle_changed")
        if {
            "input_microusd_per_mtok",
            "output_microusd_per_mtok",
        } & set(change["changes"]):
            codes.add("pricing_changed")
        if "display_name" in change["changes"]:
            codes.add("metadata_changed")
        findings.extend({"code": code, "model_id": change["id"]} for code in sorted(codes))
    findings.extend({"code": "not_observed", "model_id": model_id} for model_id in result["not_observed"])
    findings = sorted(
        {json.dumps(item, sort_keys=True): item for item in findings}.values(),
        key=lambda item: (item["code"], item["model_id"]),
    )
    return {
        "ok": True,
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "coverage": "configured_official_sources_only",
        "baseline_source_registry_digest": canonical_digest(baseline_source_registry),
        "candidate_source_registry_digest": canonical_digest(candidate_source_registry),
        "source_registry_digest": canonical_digest(candidate_source_registry),
        "catalog_digest": canonical_digest(catalog),
        "observation_digests": result["observation_digests"],
        "findings": findings,
        "quarantine_candidates": result["quarantine_proposals"],
        "requires_review": bool(findings),
        "auto_activation": False,
        "missing_means_deprecated": False,
        "network_used": False,
        "mutation_performed": False,
    }


def resolve_relative(root: Path, value: str, *, require_exists: bool = True) -> Path:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise RegistryError("invalid_path", "registry paths must be project-relative")
    candidate = root / value
    try:
        resolved = candidate.resolve(strict=require_exists)
    except OSError as exc:
        raise RegistryError("invalid_path", f"registry path is unavailable: {value}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RegistryError("path_escape", f"registry path escapes project root: {value}") from exc
    if require_exists and (not resolved.is_file() or candidate.is_symlink()):
        raise RegistryError("invalid_path_type", f"registry path must be a regular non-symlink file: {value}")
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate_sources = commands.add_parser("validate-sources")
    validate_sources.add_argument("--project-root", type=Path, required=True)
    validate_sources.add_argument("--sources", default=".exocortex/model-source-registry.json")

    validate_catalog_parser = commands.add_parser("validate-catalog")
    validate_catalog_parser.add_argument("--project-root", type=Path, required=True)
    validate_catalog_parser.add_argument("--sources", default=".exocortex/model-source-registry.json")
    validate_catalog_parser.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")

    refresh = commands.add_parser("plan-refresh")
    refresh.add_argument("--project-root", type=Path, required=True)
    refresh.add_argument("--sources", default=".exocortex/model-source-registry.json")
    refresh.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")
    refresh.add_argument("--as-of", required=True)

    discover = commands.add_parser("discover")
    discover.add_argument("--project-root", type=Path, required=True)
    discover.add_argument("--sources", default=".exocortex/model-source-registry.json")
    discover.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")
    discover.add_argument("--candidate-sources", required=True)
    discover.add_argument("--observation", action="append", required=True)
    discover.add_argument("--as-of", required=True)

    availability = commands.add_parser("validate-availability")
    availability.add_argument("--project-root", type=Path, required=True)
    availability.add_argument("--sources", default=".exocortex/model-source-registry.json")
    availability.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")
    availability.add_argument("--availability", required=True)
    availability.add_argument("--as-of", required=True)

    # Compatibility aliases for pre-C5 local test fixtures. Active
    # documentation uses the explicit command names above.
    validate = commands.add_parser("validate")
    validate.add_argument("--project-root", type=Path, required=True)
    validate.add_argument("--source-registry", default=".exocortex/model-source-registry.json")
    validate.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")
    compare = commands.add_parser("compare")
    compare.add_argument("--project-root", type=Path, required=True)
    compare.add_argument("--source-registry", default=".exocortex/model-source-registry.json")
    compare.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")
    compare.add_argument("--observation", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.project_root.resolve(strict=True)
        sources_rel = getattr(args, "sources", None) or getattr(args, "source_registry", None)
        source_registry = validate_source_registry(load_json(resolve_relative(root, sources_rel)))
        if args.command == "validate-sources":
            result = {
                "ok": True,
                "coverage": "configured_official_sources_only",
                "offline": True,
                "mutation_permitted": False,
                "source_registry_digest": canonical_digest(source_registry),
                "sources": len(source_registry["sources"]),
            }
        else:
            catalog = validate_catalog(load_json(resolve_relative(root, args.catalog)), source_registry)
        if args.command in {"validate", "validate-catalog"}:
            result = {
                "ok": True,
                "offline": True,
                "mutation_permitted": False,
                "source_registry_digest": canonical_digest(source_registry),
                "catalog_digest": canonical_digest(catalog),
                "models": len(catalog["models"]),
                "eligible_models": sum(model["routing_status"] == "eligible" for model in catalog["models"]),
            }
        elif args.command == "compare":
            observation = load_json(resolve_relative(root, args.observation))
            result = compare_observation(source_registry, catalog, observation)
        elif args.command == "plan-refresh":
            result = plan_refresh(source_registry, catalog, as_of=parse_as_of(args.as_of))
        elif args.command == "discover":
            candidate_source_registry = validate_source_registry(
                load_json(resolve_relative(root, args.candidate_sources))
            )
            observations = [load_json(resolve_relative(root, value)) for value in args.observation]
            result = discover_models(
                source_registry,
                catalog,
                candidate_source_registry,
                observations,
                as_of=parse_as_of(args.as_of),
            )
        elif args.command == "validate-availability":
            availability = validate_availability(load_json(resolve_relative(root, args.availability)))
            as_of = parse_as_of(args.as_of)
            require_fresh(source_registry, as_of, "source registry")
            require_fresh(catalog, as_of, "routing catalog")
            require_fresh(availability, as_of, "availability evidence")
            if availability["catalog_digest"] != canonical_digest(catalog):
                raise RegistryError("catalog_digest_mismatch", "availability is not bound to the supplied catalog")
            unknown = sorted(set(availability["model_ids"]) - {model["id"] for model in catalog["models"]})
            if unknown:
                raise RegistryError("unknown_available_model", "availability contains a model absent from the bound catalog")
            source_by_id = {source["id"]: source for source in source_registry["sources"]}
            model_by_id = {model["id"]: model for model in catalog["models"]}
            for model_id in availability["model_ids"]:
                for source_id in model_by_id[model_id]["source_ids"]:
                    require_source_fresh(source_by_id[source_id], as_of)
            result = {
                "ok": True,
                "as_of": args.as_of,
                "catalog_digest": canonical_digest(catalog),
                "availability_digest": canonical_digest(availability),
                "available_models": len(availability["model_ids"]),
                "offline": True,
                "mutation_permitted": False,
            }
        print(json.dumps(result, sort_keys=True))
        return 0
    except RegistryError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())

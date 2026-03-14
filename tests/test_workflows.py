"""Tests for reusable GitHub Actions workflow contracts."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _load_workflow(name: str) -> dict[str, object]:
    data = yaml.safe_load((WORKFLOWS_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def _as_mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _as_sequence(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    jobs = _as_mapping(workflow["jobs"])
    return _as_mapping(jobs[name])


def _step_by_name(steps: list[object], name: str) -> dict[str, object]:
    for step in steps:
        step_mapping = _as_mapping(step)
        if step_mapping.get("name") == name:
            return step_mapping
    raise AssertionError(f"workflow step not found: {name}")


def test_reusable_release_wrapper_preserves_hook_inputs_and_inherited_secrets() -> None:
    workflow = _load_workflow("reusable-release.yaml")
    release_job = _job(workflow, "release")

    assert release_job["uses"] == "./.github/workflows/reusable-release-advanced.yaml"
    assert release_job["secrets"] == "inherit"

    forwarded_inputs = _as_mapping(release_job["with"])
    assert forwarded_inputs["pre-create"] == "${{ inputs.pre-create }}"
    assert forwarded_inputs["post-create"] == "${{ inputs.post-create }}"
    assert forwarded_inputs["skip-publish"] == "${{ inputs.skip-publish }}"


def test_advanced_reusable_release_uses_resolved_auth_token_for_stateful_steps() -> None:
    workflow = _load_workflow("reusable-release-advanced.yaml")
    release_job = _job(workflow, "release")
    steps = _as_sequence(release_job["steps"])

    resolve_auth = _step_by_name(steps, "Resolve auth token")
    resolve_auth_env = _as_mapping(resolve_auth["env"])
    assert resolve_auth_env["APP_TOKEN"] == "${{ steps.app-token.outputs.token }}"
    assert resolve_auth_env["PUSH_TOKEN"] == "${{ secrets.push_token }}"
    assert resolve_auth_env["DEFAULT_TOKEN"] == "${{ github.token }}"
    resolve_auth_run = cast(str, resolve_auth["run"])
    assert 'SOURCE="github-app"' in resolve_auth_run
    assert 'SOURCE="push-token"' in resolve_auth_run
    assert 'SOURCE="github-token"' in resolve_auth_run

    checkout = _step_by_name(steps, "Checkout")
    checkout_with = _as_mapping(checkout["with"])
    assert checkout_with["token"] == "${{ steps.auth-token.outputs.token }}"

    configure_git = _step_by_name(steps, "Configure Git")
    configure_git_env = _as_mapping(configure_git["env"])
    assert configure_git_env["AUTH_TOKEN"] == "${{ steps.auth-token.outputs.token }}"
    configure_git_run = cast(str, configure_git["run"])
    assert "git remote set-url origin" in configure_git_run
    assert "AUTH_TOKEN" in configure_git_run

    for step_name in ["Run pre-publish script", "Stage and publish", "Run post-publish script"]:
        step = _step_by_name(steps, step_name)
        env = _as_mapping(step["env"])
        assert env["GH_TOKEN"] == "${{ steps.auth-token.outputs.token }}"


def test_ci_smoke_jobs_cover_wrapper_workflow_for_default_and_push_token_modes() -> None:
    workflow = _load_workflow("ci.yml")

    default_job = _job(workflow, "smoke-reusable-release-default-token")
    assert default_job["uses"] == "./.github/workflows/reusable-release.yaml"
    default_permissions = _as_mapping(default_job["permissions"])
    assert default_permissions["contents"] == "write"
    default_with = _as_mapping(default_job["with"])
    assert default_with["skip-publish"] is True

    push_job = _job(workflow, "smoke-reusable-release-push-token")
    assert push_job["uses"] == "./.github/workflows/reusable-release.yaml"
    push_permissions = _as_mapping(push_job["permissions"])
    assert push_permissions["contents"] == "write"
    push_with = _as_mapping(push_job["with"])
    assert push_with["skip-publish"] is True
    push_secrets = _as_mapping(push_job["secrets"])
    assert push_secrets["push_token"] == "${{ github.token }}"

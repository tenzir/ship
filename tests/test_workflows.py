"""Tests for reusable GitHub Actions workflow contracts."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


class _GitHubWorkflowLoader(yaml.SafeLoader):
    yaml_implicit_resolvers = {
        key: value[:] for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }


for ch in "OoYyNn":
    _GitHubWorkflowLoader.yaml_implicit_resolvers[ch] = [
        entry
        for entry in _GitHubWorkflowLoader.yaml_implicit_resolvers.get(ch, [])
        if entry[0] != "tag:yaml.org,2002:bool"
    ]


def _load_workflow(name: str) -> dict[str, object]:
    data = yaml.load(
        (WORKFLOWS_DIR / name).read_text(encoding="utf-8"),
        Loader=_GitHubWorkflowLoader,
    )
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


def test_load_workflow_preserves_on_key() -> None:
    workflow = _load_workflow("reusable-release.yaml")

    assert "on" in workflow
    assert True not in workflow
    workflow_on = _as_mapping(workflow["on"])
    assert "workflow_call" in workflow_on


def test_reusable_release_wrapper_preserves_hook_inputs_and_inherited_secrets() -> None:
    workflow = _load_workflow("reusable-release.yaml")
    workflow_call = _as_mapping(_as_mapping(workflow["on"])["workflow_call"])
    workflow_secrets = _as_mapping(workflow_call["secrets"])
    release_job = _job(workflow, "release")

    assert release_job["uses"] == "./.github/workflows/reusable-release-advanced.yaml"
    permissions = _as_mapping(release_job["permissions"])
    assert permissions["contents"] == "write"
    assert release_job["secrets"] == "inherit"
    assert _as_mapping(workflow_secrets["hook_env"])["required"] is False

    forwarded_inputs = _as_mapping(release_job["with"])
    assert forwarded_inputs["pre-create"] == "${{ inputs.pre-create }}"
    assert forwarded_inputs["post-create"] == "${{ inputs.post-create }}"
    assert forwarded_inputs["skip-publish"] == "${{ inputs.skip-publish }}"
    assert forwarded_inputs["github_app_id"] == "${{ inputs.github_app_id }}"
    assert forwarded_inputs["use_push_token"] == "${{ inputs.use_push_token }}"
    assert forwarded_inputs["git_user_name"] == "${{ inputs.git_user_name }}"
    assert forwarded_inputs["git_user_email"] == "${{ inputs.git_user_email }}"
    assert forwarded_inputs["sign_commits"] == "${{ inputs.sign_commits }}"
    assert forwarded_inputs["sign_tags"] == "${{ inputs.sign_tags }}"


def test_advanced_reusable_release_allows_inherited_app_key_when_app_auth_is_unused() -> None:
    workflow = _load_workflow("reusable-release-advanced.yaml")
    workflow_call = _as_mapping(_as_mapping(workflow["on"])["workflow_call"])
    workflow_inputs = _as_mapping(workflow_call["inputs"])
    workflow_secrets = _as_mapping(workflow_call["secrets"])

    assert _as_mapping(workflow_inputs["github_app_id"])["required"] is False
    assert _as_mapping(workflow_inputs["use_push_token"])["required"] is False
    assert _as_mapping(workflow_secrets["push_token"])["required"] is False
    assert _as_mapping(workflow_secrets["github_app_private_key"])["required"] is False
    assert _as_mapping(workflow_secrets["gpg_private_key"])["required"] is False
    assert _as_mapping(workflow_secrets["hook_env"])["required"] is False

    release_job = _job(workflow, "release")
    steps = _as_sequence(release_job["steps"])

    validate_inputs = _step_by_name(steps, "Validate release inputs")
    validate_inputs_run = cast(str, validate_inputs["run"])
    assert "Input 'github_app_id' requires secret 'github_app_private_key'." in validate_inputs_run
    assert "Input 'use_push_token' requires secret 'push_token'." in validate_inputs_run
    assert (
        "Secret 'github_app_private_key' requires input 'github_app_id'." not in validate_inputs_run
    )


def test_advanced_reusable_release_uses_resolved_auth_token_for_stateful_steps() -> None:
    workflow = _load_workflow("reusable-release-advanced.yaml")
    release_job = _job(workflow, "release")
    assert release_job["name"] == "release"
    steps = _as_sequence(release_job["steps"])

    resolve_auth = _step_by_name(steps, "Resolve auth token")
    resolve_auth_env = _as_mapping(resolve_auth["env"])
    assert resolve_auth_env["APP_TOKEN"] == "${{ steps.app-token.outputs.token }}"
    assert resolve_auth_env["USE_PUSH_TOKEN"] == "${{ inputs.use_push_token }}"
    assert resolve_auth_env["PUSH_TOKEN"] == "${{ secrets.push_token }}"
    assert resolve_auth_env["DEFAULT_TOKEN"] == "${{ github.token }}"
    resolve_auth_run = cast(str, resolve_auth["run"])
    assert 'SOURCE="github-app"' in resolve_auth_run
    assert 'SOURCE="push-token"' in resolve_auth_run
    assert 'SOURCE="github-token"' in resolve_auth_run
    assert '[ "$USE_PUSH_TOKEN" = "true" ]' in resolve_auth_run
    assert "::add-mask::$TOKEN" in resolve_auth_run

    checkout = _step_by_name(steps, "Checkout")
    checkout_with = _as_mapping(checkout["with"])
    assert checkout_with["token"] == "${{ steps.auth-token.outputs.token }}"

    workflow_source = _step_by_name(steps, "Resolve workflow source")
    workflow_source_run = cast(str, workflow_source["run"])
    assert 'echo "owner=${REPOSITORY%/*}"' in workflow_source_run
    assert 'echo "name=${REPOSITORY#*/}"' in workflow_source_run

    workflow_source_app_token = _step_by_name(steps, "Generate workflow source app token")
    assert (
        workflow_source_app_token["if"]
        == "${{ inputs.github_app_id != '' && steps.workflow-source.outputs.repository != github.repository }}"
    )
    assert workflow_source_app_token["continue-on-error"] is True
    workflow_source_app_token_with = _as_mapping(workflow_source_app_token["with"])
    assert workflow_source_app_token_with["owner"] == "${{ steps.workflow-source.outputs.owner }}"
    assert (
        workflow_source_app_token_with["repositories"]
        == "${{ steps.workflow-source.outputs.name }}"
    )

    workflow_source_token = _step_by_name(steps, "Resolve workflow source token")
    workflow_source_token_env = _as_mapping(workflow_source_token["env"])
    assert (
        workflow_source_token_env["SOURCE_APP_TOKEN"]
        == "${{ steps.workflow-source-app-token.outputs.token }}"
    )
    assert workflow_source_token_env["DEFAULT_TOKEN"] == "${{ steps.auth-token.outputs.token }}"
    workflow_source_token_run = cast(str, workflow_source_token["run"])
    assert 'SOURCE="workflow-source-github-app"' in workflow_source_token_run
    assert 'SOURCE="primary-auth"' in workflow_source_token_run
    assert "::add-mask::$TOKEN" in workflow_source_token_run

    workflow_source_checkout = _step_by_name(steps, "Checkout tenzir-ship source")
    workflow_source_checkout_with = _as_mapping(workflow_source_checkout["with"])
    assert (
        workflow_source_checkout_with["token"] == "${{ steps.workflow-source-token.outputs.token }}"
    )

    configure_git = _step_by_name(steps, "Configure Git")
    configure_git_env = _as_mapping(configure_git["env"])
    assert configure_git_env["AUTH_TOKEN"] == "${{ steps.auth-token.outputs.token }}"
    assert configure_git_env["GITHUB_SERVER_URL"] == "${{ github.server_url }}"
    assert (
        configure_git_env["GPG_ENABLED"] == "${{ steps.optional-credentials.outputs.has_gpg_key }}"
    )
    assert configure_git_env["SIGN_COMMITS"] == "${{ inputs.sign_commits }}"
    assert configure_git_env["SIGN_TAGS"] == "${{ inputs.sign_tags }}"
    configure_git_run = cast(str, configure_git["run"])
    assert 'if [ "$GPG_ENABLED" = "true" ]; then' in configure_git_run
    assert 'git config --global commit.gpgsign "$SIGN_COMMITS"' in configure_git_run
    assert 'git config --global tag.gpgsign "$SIGN_TAGS"' in configure_git_run
    assert "git config --global commit.gpgsign false" in configure_git_run
    assert "git config --global tag.gpgsign false" in configure_git_run
    assert "git config --global --unset-all user.signingkey || true" in configure_git_run
    assert 'server_host="${GITHUB_SERVER_URL#https://}"' in configure_git_run
    assert "git remote set-url origin" in configure_git_run
    assert "AUTH_TOKEN" in configure_git_run
    assert "${server_host}/${{ github.repository }}.git" in configure_git_run

    for step_name in [
        "Run pre-create script",
        "Run post-create script",
        "Run pre-publish script",
        "Run post-publish script",
    ]:
        step = _step_by_name(steps, step_name)
        env = _as_mapping(step["env"])
        assert env["HOOK_ENV"] == "${{ secrets.hook_env }}"
        run = cast(str, step["run"])
        assert 'if [ -n "$HOOK_ENV" ]; then' in run
        assert ". <(printf '%s\\n' \"$HOOK_ENV\")" in run

    for step_name in ["Run pre-publish script", "Stage and publish", "Run post-publish script"]:
        step = _step_by_name(steps, step_name)
        env = _as_mapping(step["env"])
        assert env["GH_TOKEN"] == "${{ steps.auth-token.outputs.token }}"


def test_repo_release_workflow_wires_github_app_auth_and_signing() -> None:
    workflow = _load_workflow("release.yaml")
    release_job = _job(workflow, "release")

    assert release_job["uses"] == "./.github/workflows/reusable-release.yaml"
    permissions = _as_mapping(release_job["permissions"])
    assert permissions["contents"] == "write"

    forwarded_inputs = _as_mapping(release_job["with"])
    assert forwarded_inputs["github_app_id"] == "${{ vars.TENZIR_GITHUB_APP_ID }}"
    assert forwarded_inputs["git_user_name"] == "tenzir-bot"
    assert forwarded_inputs["git_user_email"] == "engineering@tenzir.com"

    forwarded_secrets = _as_mapping(release_job["secrets"])
    assert (
        forwarded_secrets["github_app_private_key"]
        == "${{ secrets.TENZIR_GITHUB_APP_PRIVATE_KEY }}"
    )
    assert forwarded_secrets["gpg_private_key"] == "${{ secrets.TENZIR_BOT_GPG_SIGNING_KEY }}"


def test_ci_smoke_jobs_use_concise_names_and_cover_default_and_push_token_modes() -> None:
    workflow = _load_workflow("ci.yml")

    default_job = _job(workflow, "smoke-reusable-release-default-token")
    assert default_job["name"] == "Release smoke (default token)"
    assert default_job["uses"] == "./.github/workflows/reusable-release-advanced.yaml"
    default_permissions = _as_mapping(default_job["permissions"])
    assert default_permissions["contents"] == "write"
    default_with = _as_mapping(default_job["with"])
    assert default_with["skip-publish"] is True

    push_job = _job(workflow, "smoke-reusable-release-push-token")
    assert push_job["name"] == "Release smoke (push token)"
    assert push_job["uses"] == "./.github/workflows/reusable-release-advanced.yaml"
    push_permissions = _as_mapping(push_job["permissions"])
    assert push_permissions["contents"] == "write"
    push_with = _as_mapping(push_job["with"])
    assert push_with["use_push_token"] is True
    assert push_with["skip-publish"] is True
    push_secrets = _as_mapping(push_job["secrets"])
    assert push_secrets["push_token"] == "${{ secrets.GITHUB_TOKEN }}"

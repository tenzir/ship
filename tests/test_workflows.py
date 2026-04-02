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


def test_reusable_release_is_the_only_reusable_release_workflow() -> None:
    workflow = _load_workflow("reusable-release.yaml")
    release_job = _job(workflow, "release")
    workflow_call = _as_mapping(_as_mapping(workflow["on"])["workflow_call"])
    inputs = _as_mapping(workflow_call["inputs"])

    assert not (WORKFLOWS_DIR / "reusable-release-advanced.yaml").exists()
    assert release_job["runs-on"] == "ubuntu-latest"
    assert "uses" not in release_job

    for input_name in [
        "pre-create",
        "post-create",
        "pre-publish",
        "post-publish",
        "skip-publish",
        "publish-no-latest-on-non-main",
        "copy-release-to-main-on-non-main",
        "update-latest-branch-on-main",
        "github_app_id",
        "git_user_name",
        "git_user_email",
        "sign_commits",
        "sign_tags",
    ]:
        assert input_name in inputs


def test_reusable_release_signing_defaults_are_opt_in() -> None:
    workflow = _load_workflow("reusable-release.yaml")
    workflow_call = _as_mapping(_as_mapping(workflow["on"])["workflow_call"])
    inputs = _as_mapping(workflow_call["inputs"])
    assert _as_mapping(inputs["sign_commits"])["default"] is False
    assert _as_mapping(inputs["sign_tags"])["default"] is False


def test_reusable_release_validates_optional_auth_and_signing_inputs() -> None:
    workflow = _load_workflow("reusable-release.yaml")
    release_job = _job(workflow, "release")
    steps = _as_sequence(release_job["steps"])

    validate_inputs = _step_by_name(steps, "Validate workflow inputs")
    validate_inputs_env = _as_mapping(validate_inputs["env"])
    assert validate_inputs_env["GPG_PRIVATE_KEY"] == "${{ secrets.gpg_private_key }}"
    assert validate_inputs_env["SIGN_COMMITS"] == "${{ inputs.sign_commits }}"
    assert validate_inputs_env["SIGN_TAGS"] == "${{ inputs.sign_tags }}"
    validate_inputs_run = cast(str, validate_inputs["run"])
    assert "Input 'github_app_id' requires secret 'github_app_private_key'." in validate_inputs_run
    assert (
        "Inputs 'sign_commits' or 'sign_tags' require secret 'gpg_private_key'."
        in validate_inputs_run
    )
    assert (
        "Secret 'github_app_private_key' requires input 'github_app_id'." not in validate_inputs_run
    )


def test_reusable_release_uses_resolved_auth_token_for_stateful_steps() -> None:
    workflow = _load_workflow("reusable-release.yaml")
    release_job = _job(workflow, "release")
    steps = _as_sequence(release_job["steps"])

    resolve_optional_credentials = _step_by_name(steps, "Resolve optional credentials")
    resolve_optional_credentials_env = _as_mapping(resolve_optional_credentials["env"])
    assert resolve_optional_credentials_env["SIGN_COMMITS"] == "${{ inputs.sign_commits }}"
    assert resolve_optional_credentials_env["SIGN_TAGS"] == "${{ inputs.sign_tags }}"
    resolve_optional_credentials_run = cast(str, resolve_optional_credentials["run"])
    assert 'echo "use_gpg_signing=true" >> "$GITHUB_OUTPUT"' in resolve_optional_credentials_run
    assert 'echo "use_gpg_signing=false" >> "$GITHUB_OUTPUT"' in resolve_optional_credentials_run

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

    setup_gpg_signing = _step_by_name(steps, "Set up GPG signing")
    assert (
        setup_gpg_signing["if"]
        == "${{ steps.optional-credentials.outputs.use_gpg_signing == 'true' }}"
    )

    configure_git = _step_by_name(steps, "Configure Git")
    configure_git_env = _as_mapping(configure_git["env"])
    assert configure_git_env["AUTH_TOKEN"] == "${{ steps.auth-token.outputs.token }}"
    assert configure_git_env["GITHUB_SERVER_URL"] == "${{ github.server_url }}"
    assert (
        configure_git_env["USE_GPG_SIGNING"]
        == "${{ steps.optional-credentials.outputs.use_gpg_signing }}"
    )
    configure_git_run = cast(str, configure_git["run"])
    assert "git config --global --unset-all user.signingkey || true" in configure_git_run
    assert "git config --global commit.gpgsign false" in configure_git_run
    assert "git config --global tag.gpgsign false" in configure_git_run
    assert 'server_host="${GITHUB_SERVER_URL#https://}"' in configure_git_run
    assert "git remote set-url origin" in configure_git_run
    assert "AUTH_TOKEN" in configure_git_run
    assert "${server_host}/${{ github.repository }}.git" in configure_git_run

    for step_name in ["Run pre-publish script", "Stage and publish", "Run post-publish script"]:
        step = _step_by_name(steps, step_name)
        env = _as_mapping(step["env"])
        assert env["GH_TOKEN"] == "${{ steps.auth-token.outputs.token }}"


def test_ci_smoke_jobs_cover_reusable_release_for_default_and_push_token_modes() -> None:
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


def test_repo_release_workflow_opts_into_signed_releases_explicitly() -> None:
    workflow = _load_workflow("release.yaml")
    release_job = _job(workflow, "release")

    forwarded_inputs = _as_mapping(release_job["with"])
    assert forwarded_inputs["github_app_id"] == "${{ vars.TENZIR_GITHUB_APP_ID }}"
    assert forwarded_inputs["sign_commits"] is True
    assert forwarded_inputs["sign_tags"] is True

    forwarded_secrets = _as_mapping(release_job["secrets"])
    assert (
        forwarded_secrets["github_app_private_key"]
        == "${{ secrets.TENZIR_GITHUB_APP_PRIVATE_KEY }}"
    )
    assert forwarded_secrets["gpg_private_key"] == "${{ secrets.TENZIR_BOT_GPG_SIGNING_KEY }}"

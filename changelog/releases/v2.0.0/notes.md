Tenzir Ship now keeps projects on major version zero when unreleased entries include breaking changes, automatically selecting the next minor release instead of jumping to 1.0.0. Projects can still explicitly request 1.0.0 when declaring their first stable release.

## 💥 Breaking changes

### Minor bumps for pre-1.0 breaking changes

Automatic release creation now keeps projects on major version zero when their unreleased entries include breaking changes. For example, a breaking entry after `v0.4.2` now produces `v0.5.0` instead of `v1.0.0`.

To declare the first stable release, request it explicitly:

```sh
tenzir-ship release create --major --yes
```

You can also pass `1.0.0` as the release version. Breaking entries continue to trigger major bumps after a project reaches `v1.0.0`. Active release candidates remain on their explicitly selected target during continuation and promotion. If multiple outstanding release-candidate series make that target ambiguous, `stats` warns and reports no next version instead of failing.

*By @mavam and @codex in #42.*

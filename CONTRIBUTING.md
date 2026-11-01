# Contributing

Original project-owned code is licensed under **GPL-3.0-only**; see
[LICENSE](LICENSE) and [COPYRIGHT](COPYRIGHT). By intentionally submitting an
original code/documentation contribution for inclusion, you submit it under
the applicable GPL-3.0-only project terms. Contribute only work you have the
authority to license. You retain copyright in your contribution; no Contributor
License Agreement or copyright assignment is introduced.

Keep existing legitimate copyright/license notices. Add your own attribution
where appropriate; do not attribute somebody else's work to Lumin0usX. Identify
any third-party portions, their provenance and original terms explicitly;
submission does not automatically relicense them. Incompatible or uncertain
material needs review before acceptance. Brand artwork is outside the new
software grant: propose any asset changes with their actual permissions and
see [BRAND-NOTICE.md](BRAND-NOTICE.md).

Source publication remains a separate owner decision; public Windows and
macOS binary releases remain **BLOCKED**. Contribution acceptance or the GPL
decision does not clear those gates. See [third-party notices](THIRD_PARTY_NOTICES.md)
and [license decision](legal/LICENSE-RECOMMENDATION.md).

Keep changes focused. The application uses Python/pywebview and plain HTML,
CSS and JavaScript; preserve the existing UI and Windows x64/macOS ARM64 support.
Do not add DRM bypass, unauthorized authentication, automatic cookie extraction,
or unreviewed external executables. Document dependency licenses and actual
redistribution/source requirements when proposing a dependency change.

Use a clean, native Python environment compatible with the dependencies and install
`requirements.txt`. PyInstaller is needed for packaging/artifact inspection, not
for ordinary source edits. See the platform READMEs for native prerequisites.

```bash
python -m unittest discover -s tests
node tests/test_theme.cjs
node tests/test_appearance.cjs
node tests/test_workspace.cjs
node tests/test_snapshot_polling.cjs
node tests/test_fonts.cjs
node tests/test_i18n.cjs
node tests/test_platform_directory.cjs
python repository_audit.py --fail-on-secrets --output dist/audit/history.json
```

Report passed/failed/skipped/not-executed separately. Tests of legacy Tk require
an importable `_tkinter` binding; normal pywebview use does not. Local HTTP
integration tests require permission to bind **127.0.0.1**. Never change them to
listen on all interfaces, hide failures, or fabricate native acceptance.

For an online dependency audit, install the development tool
`pip-audit==2.10.1` and run `python -m pip_audit --strict`. Do not use `--fix`
without reviewing the proposed changes. A failed/unavailable database is not a
clean result. Native Windows and macOS checks must be assessed separately;
a workflow definition is not evidence that it ran.

Before submitting, inspect `git diff --check` and the staged diff. Never include
cookies, tokens, browser profiles, media, generated apps or raw diagnostic dumps.
Use only media you are authorized to test. Public source publication and binary
publication are separate decisions. Current binary releases are not approved.

# Releasing spancheck to PyPI

spancheck is MIT-licensed and published as `spancheck`. Releases are cut from `main` after tests are green.

## One-time setup
- A PyPI account, and an **API token** (PyPI → Account settings → API tokens). Keep it out of the repo.
- `pip install --upgrade build twine`

## Cut a release
1. Bump `version` in `pyproject.toml` (semver; a breaking change to the audit-log schema is a **major** bump — see
   `docs/AUDIT-LOG.md`).
2. Ensure the suite is green: `pytest -q`.
3. Build the artifacts (clean `dist/` first):
   ```bash
   rm -rf dist build *.egg-info
   python -m build            # produces dist/spancheck-<ver>-py3-none-any.whl and .tar.gz
   twine check dist/*         # metadata/README render check
   ```
4. Upload (the token is your manual step — never commit it):
   ```bash
   twine upload dist/*        # username: __token__   password: <your PyPI API token>
   ```
   Or set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<token>` in the environment for a non-interactive upload.
5. Tag the release: `git tag v<ver> && git push origin v<ver>`.
6. Verify: `pip install spancheck==<ver>` in a fresh venv, then `spancheck --version`.

## Notes
- The wheel bundles the judge prompt (`prompts/*.txt`) via `[tool.setuptools.package-data]`; `twine check` and a
  fresh-venv `spancheck.load_prompt("entailment_v1")` confirm it ships.
- No secrets or `.env` are packaged (`.gitignore` + the `src/` layout keep them out).
- First release: **0.1.0**.

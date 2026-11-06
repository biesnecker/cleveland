# Contributing

## Development

```
uv run pytest                        # the default Python
uv run --python 3.11 pytest          # a specific Python
uv run --with mypy mypy --strict cleveland tests/typing_usage.py
```

Tests run on a virtual-clock event loop (`tests/helpers.py`), so sleeps,
timeouts and broadcaster intervals finish instantly and the same way every
time, and a deadlock fails the test instead of hanging it. Use `run()` from
there instead of `asyncio.run()`, and `until_idle()` instead of a short sleep
to let other tasks catch up.

CI (`.github/workflows/ci.yml`) runs the tests on Python 3.11–3.14 on Linux
and Windows (plus macOS on 3.14), type-checks with `mypy --strict`, and tests
the built wheel, on every push and pull request.

## Releasing

1. Bump `__version__` in `cleveland/version.py`.
2. In `CHANGELOG.md`, change that version's heading from `(unreleased)` to
   the release date, e.g. `## 1.2.3 (2027-01-31)`.
3. Merge to `master`.
4. Tag that commit and push the tag:

   ```
   git tag v1.2.3
   git push origin v1.2.3
   ```

The release workflow (`.github/workflows/release.yml`) then:

- checks the tag matches the version, is on `master`, and has a dated
  changelog entry;
- runs the full CI matrix on the tagged commit;
- publishes the built distributions to PyPI;
- creates the GitHub release, using the changelog section as its notes.

Nothing is published if any check or test fails. Fix the problem, delete the
tag (`git push --delete origin v1.2.3 && git tag -d v1.2.3`) and tag again.
Once a version is on PyPI it can't be re-uploaded, so a broken release needs
a new version number.

### PyPI setup

The workflow uses
[trusted publishing](https://docs.pypi.org/trusted-publishers/), so there is
no API token to manage. Before the first release from this workflow, add a
trusted publisher for the existing `cleveland` project on PyPI with:

- Owner: `biesnecker`
- Repository: `cleveland`
- Workflow: `release.yml`
- Environment: `pypi`

and create a `pypi` environment in the repository settings that only allows
deployments from `v*` tags. If the workflow file or environment is renamed,
update the publisher at
<https://pypi.org/manage/project/cleveland/settings/publishing/>.

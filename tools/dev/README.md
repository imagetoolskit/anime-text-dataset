# Development one-offs

These scripts are **not** part of the test suite, the package, or the release
pipeline. They are scratch diagnostics kept from earlier debugging sessions.

- Several hardcode the absolute path `C:\Users\Umar\anime-text-dataset`.
- `wipe_derived.py`, `reset_phases.py`, `reset_episodes.py` and `fix_cp.py`
  write to (or delete rows from) the working database.
- None of them is imported by `src/`, `scripts/` or the tests.

Do not run them against a database you care about. The maintained entry points
are `python -m src.cli <stage>` and the scripts in `scripts/`.

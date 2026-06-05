<!--
Thanks for the contribution! Keep PRs focused — one logical change each.
For anything larger than a small fix, please open an issue first.
-->

## What this changes

<!-- A short description of the change and the why behind it. -->

## Related issue

<!-- e.g. Closes #123 — required for non-trivial changes. -->

## Checklist

- [ ] Tests pass (`pytest` from root, `cd ui && npm test`)
- [ ] Added/updated tests for new behavior (where it makes sense)
- [ ] Change is scoped — no unrelated reformatting or drive-by edits
- [ ] Docs updated if behavior/usage changed (not README — owned separately)
- [ ] Keeps the boundary intact: the engine/API still make **no LLM calls** and
      send nothing off the user's machine

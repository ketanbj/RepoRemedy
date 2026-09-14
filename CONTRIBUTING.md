# Contributing

## Pull request size

Aim for 300–500 changed code lines per PR, with a maximum of 500. Smaller PRs are
welcome when they deliver a complete, independently testable change. Count additions
plus deletions, including tests, scripts, and build/CI configuration. Keep the tests
for a behavior with its implementation; do not remove tests to meet the limit.

The `PR size / size` check compares each PR head with the merge base of its target
branch, so stacked PRs count only their own changes. It counts Python, shell,
JavaScript/TypeScript, TOML, YAML, Dockerfiles, Makefiles, and `.env.example` files.
Fixtures, documentation, lockfiles, and data files are excluded from the code limit
and reported separately. Keep those changes focused and reviewable as well.

Run the same check locally with the actual base and head commit references:

```sh
python scripts/check_pr_size.py BASE_SHA HEAD_SHA
python scripts/test_pr_size.py
```

When a PR exceeds the limit, split it along module or behavior boundaries and keep
each slice buildable and tested. Update PR dependencies and the delivery map when
changing the stack. Keep commits signed with the repository owner's configured key.

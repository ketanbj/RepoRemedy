# Review, publish, act and respond

1. Run `preview`; read the generated README, individual proposals and diffs.
2. Choose proposal IDs. Run `reporemedy publish runs/first --select ID1,ID2`.
   The CLI lists the target and selections and asks for confirmation. `--yes` is
   explicit confirmation for unattended use. There is no automatic publish-all.
3. Settings suggestions become issues. File changes become **draft** PRs, with
   required project fields clearly listed. Maintainers can fill the template,
   adapt the diff, mark ready for review and merge using normal GitHub controls.
4. Run `reporemedy feedback runs/first` to collect decisions, reviews and comments.

The published item includes original evidence, purpose, impact, effort, action
steps, verification and required inputs. The full audit report is optional context.

Publication uses the authenticated account. A token needs issue write permission
for settings issues, and contents/pull-request write permission for direct PRs.
When the account cannot push to a target, RepoRemedy creates/uses its fork and
opens a cross-fork draft PR. Organization policy can prohibit forking or publication;
those failures are reported. Do not put tokens in commands, manifests or reports.

Every publish verifies the preview's base commit and original file SHAs/content.
If the default branch changed, preview and review again. Publication never force
pushes, overwrites another branch, enables settings, or merges PRs.
Deterministic markers prevent re-opening existing suggestions, including declined
or closed ones. Pagination covers all issue states. Publication has a per-run local
lock; coordinate auditors across different machines/runs to avoid concurrent issue
creation races (GitHub issues provide no atomic idempotency key).

`publication.json` records each outcome. A failed write can have succeeded remotely:
rerun publication to reconcile markers, or inspect GitHub if the preview became stale.
A crash may leave `.publish.lock`; check for a running process and remote changes before
removing that lock. Branches left by failed PR creation are resumed only if their
complete tree and base match the reviewed change. Fork preparation may require retry.

Merged PRs count as accepted. For settings issues, maintainers can comment on a line:
`reporemedy: accepted`, `reporemedy: declined`, `reporemedy: needs-adjustment`, or
`reporemedy: too-difficult`. Only OWNER/MEMBER/COLLABORATOR decisions are classified;
all comments remain available as feedback. Closing an issue alone does not mean acceptance.
Acceptance among all published items and among decided items have separate denominators;
pending and adjustment requests remain separate. GitHub acceptance is not proof that a
setting was changed; follow-up verification remains the auditor's responsibility.

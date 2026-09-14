# Report interoperability

Choose `--report-type repoauditor` or `--report-type ossf-scorecard` explicitly.
RepoRemedy never imports or invokes either assessment tool.

* RepoAuditor: UTF-8 text saved with `--output`. The supported panel layout was
  inspected at gt-csse/RepoAuditor commit `c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67`,
  `src/RepoAuditor/Display.py`. Error/Warning panels become candidates; successful
  and not-applicable panels are ignored. Keep panel borders and full titles intact.
  Text reports contain no reliable repository identity or commit: supply the right
  `--repo` yourself. The fixture is synthetic and uses the actual panel grammar.
* Scorecard: v5.x JSON produced with `--format json`, containing `repo`,
  `scorecard.version`, and `checks`. Preserve reasons and details. Scores 0–9 are
  candidates; -1 means unavailable, not a proven gap. Unknown/new schemas fail
  explicitly. We do not promise support for future major versions.
* OSPO prototype envelope: `{meta, scorecard}` or a list of these. Exactly one
  report must match the selected repository. Export one scan from multi-scan history
  yourself; RepoRemedy does not silently choose an old scan. Contact metadata is discarded.

Inputs are limited to 20 MiB. Report identity mismatches, malformed exports and
truncated panels fail before remediation. A parser success is not a fresh audit.

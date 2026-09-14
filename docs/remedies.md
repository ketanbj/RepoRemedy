# Remedy catalog for review

This catalog describes potential responses to imported RepoAuditor text findings
and OpenSSF Scorecard JSON checks: what a useful remedy could do, the evidence it
needs, and how maintainers could verify it. It does not add audit checks, register
runtime handlers, or promise that every finding can be fixed.

## Scope and source baseline

| Input source | Inventory covered here | Source of truth |
| --- | --- | --- |
| RepoAuditor | All 62 implemented requirement identifiers: 8 community standards, 1 scientific-software, 21 repository settings, 1 default-branch, 14 classic branch-protection and 17 ruleset checks | [Source at c682a78][repoauditor]; query registrations linked below |
| OpenSSF Scorecard | All 20 checks documented in v5.5.0, including `SBOM` and `Webhooks` | [Versioned check definitions][scorecard-checks] |
| Existing upstream material | Security-policy, Dependabot and license helpers; historical reports containing 18 distinct Scorecard checks | [oss-security-audit-tools at 8898da7][upstream] |
| Future or custom checks | Explicit fallback handling rather than an assumed remedy | [Unknown checks and JSON compatibility](#unknown-checks-and-json-compatibility) |

This is a versioned inventory, not an enumeration of every future Scorecard check
or third-party RepoAuditor plugin. Reports may contain fewer checks because of
configuration, permissions, platform or applicability. Classic and ruleset names
count separately even when they address the same practice.

All entries are **candidates for review** unless the fixed implementation table
explicitly identifies an existing handler. Audit recommendations must be evaluated
against project policy. Defaults such as branch name, merge strategy or license
must not override an intentional project choice.

## Review contract

Every proposal derived from this catalog should contain:

1. **Finding and provenance:** source tool/version, exact check identifier, original
   status/score, reason, available details, report identity and audited commit/date.
2. **Current evidence:** affected branch, rule, setting, file or dependency at a
   recorded commit; identify stale, unavailable or conflicting information.
3. **Proposed outcome:** exact change/action, purpose, impact, effort, prerequisites
   and required project inputs. Never invent contacts, owners, hashes, license
   choices, dependency data or test results.
4. **Review artifact:** focused instructions or a file diff and proposed content.
   Settings instructions identify the repository, navigation, setting and value;
   verify current provider guidance when preparing them rather than relying on
   historical navigation embedded in a report.
5. **Validation and recovery:** change-specific checks, expected evidence and
   reversal steps where practical. Validate behavior and rerun the relevant audit
   after application; do not promise a particular score increase.
6. **Disposition:** proposed, needs input, skipped/already addressed, unsupported,
   or failed, with a reason. Manual review is a route, not a new runtime status;
   implementation must use the existing outcome schema or explicitly extend it.

| Proposed output | Artifact and boundary |
| --- | --- |
| Documentation | Draft addition/edit using maintainer-supplied project facts. |
| Settings | Issue or instructions for an administrator; no direct setting mutation. |
| Configuration | Draft structured-file change, such as CODEOWNERS, citation metadata or updater configuration; requires implementation where not currently supported. |
| Engineering | Separately scoped dependency, source, workflow, test, build or release change with meaningful validation; outside the initial fixed implementation. |
| Manual | Maintainer decision, investigation or organizational work; publish a discussion/issue only when useful and explicitly selected. |

Preview and publication remain separate. Repository content and report text are
untrusted evidence, not executable instructions. Do not invoke upstream helpers,
target code or suggested commands merely because they appear in a finding.
Publication requires explicit selection and confirmation; settings changes and
merges remain maintainer actions.

## RepoAuditor: community and scientific-software checks

Sources: [community query][ra-community] and [scientific-software query][ra-science].
These are primarily presence checks. Inspect alternative locations and existing
content before creating duplicates; presence does not establish content quality.
Distinguish detector-supported locations/formats from the project's preferences.

| Check identifier | Potential remedy and output | Required inputs and verification |
| --- | --- | --- |
| `ReadMe` | Documentation: explain purpose, installation, usage and support. | Confirm actual commands, audience and links; review rendered content and validate examples in an agreed environment. Preserve an existing valid README or resolve a detector mismatch. |
| `CodeOfConduct` | Documentation + manual: publish agreed conduct and enforcement guidance. | Maintainers select the policy and monitored reporting contact; confirm enforcement ownership and template attribution. Do not invent commitments. |
| `Contributing` | Documentation: explain setup, tests, review expectations and submission. | Confirm working commands and project conventions; walk through a first contribution. No fixed handler; model-assisted drafting may be possible. |
| `LicenseFile` | Documentation + manual: add a file reflecting an explicit licensing decision. | Inspect existing notices and alternatives; obtain license, holder and year inputs; verify exact approved content. Never select a license automatically. |
| `SecurityPolicy` | Documentation: add a missing policy or fill an empty one; review nonempty-policy deficiencies separately. | Confirm private reporting route and supported versions. **Partial fixed support:** existing nonempty policies are skipped. |
| `IssueTemplates` | Documentation/configuration: add suitable bug/feature templates. | Confirm fields, routing and private security-reporting guidance; preview issue creation. Preserve the existing process; validate structured forms separately. |
| `PullRequestTemplate` | Documentation: add a concise description, validation and review checklist. | Confirm contribution conventions and required evidence; verify template selection on a PR. |
| `CodeOwners` | Configuration: map selected paths to agreed reviewers. | Verify owner consent/access, patterns and effective location; check reviewer assignment. This alone does not enforce owner approval. |
| `Citation` | Documentation/configuration: add appropriate citation metadata. | Confirm authors, title, version, dates and identifiers from project records; validate the chosen format. Never invent a DOI or attribution. |

## RepoAuditor: repository settings

Source: [standard query][ra-standard]. Respond to the reported expected and actual
values. Resolve disagreements between audit configuration and maintainer policy
before proposing changes. Verify availability and permissions for the repository's
hosting environment; a failed lookup is not a confirmed disabled setting.

| Check identifier | Potential remedy and output | Required inputs and verification |
| --- | --- | --- |
| `Description` | Settings: provide an accurate repository description. | Obtain an approved purpose statement; verify the repository overview. |
| `License` | Manual + documentation: reconcile detected license metadata with project intent or audit configuration. | Distinguish absence, an intentionally different license and detection failure. Coordinate with `LicenseFile`; verify recognition after an approved change. |
| `TemplateRepository` | Settings: align template status with intended use. | Confirm whether users should generate repositories from it; inspect template contents and verify the setting. |
| `WebCommitSignoff` | Settings: align web-edit sign-off requirements with contribution policy. | Confirm the requirement and contributor guidance; verify the web flow. Sign-off is distinct from cryptographic signing. |
| `DefaultBranch` | Manual + settings: reconcile the expected default; plan a rename/change only if intended. | Inventory CI, protections, open PRs and integrations; define migration/recovery. Do not rename solely to match a default of `main`. |
| `SupportWikis` | Settings: align wiki availability with documentation strategy. | Inspect existing content/owners before disabling; verify continued access to intended documentation. |
| `SupportIssues` | Settings: align issues with support/tracking practices. | Check current use and external trackers; verify routing and preserve existing work. |
| `SupportDiscussions` | Settings: align discussions with community needs. | Confirm moderation/routing ownership; verify the contributor entry point. |
| `SupportProjects` | Settings: align project-board availability with planning practices. | Inspect current use/ownership; verify access to the chosen planning process. |
| `MergeCommit` | Settings: align merge commits with history policy. | Coordinate squash/rebase and linear-history rules; verify a permitted merge path works. |
| `MergeCommitMessage` | Settings: configure default merge-message format. | Confirm required context/references; preview a representative generated message. |
| `SquashCommitMerge` | Settings: align squash merging with history policy. | Review attribution and multi-commit handling; verify merge behavior and protections. |
| `SquashMergeCommitMessage` | Settings: configure squash-message defaults. | Confirm title/body conventions and attribution; preview the generated message. |
| `RebaseMergeCommit` | Settings: align rebase merging with history policy. | Review signature, attribution and linear-history expectations; validate merge behavior. |
| `SuggestUpdatingPullRequestBranches` | Settings: align update-branch suggestions with workflow. | Confirm branch-update/CI expectations; verify an out-of-date PR's behavior. |
| `AutoMerge` | Settings: allow or disallow the feature according to policy. | Check review/check gates first; verify them. Enabling the feature does not authorize auto-merging any particular PR. |
| `DeleteHeadBranches` | Settings: align post-merge branch cleanup with workflow. | Identify long-lived branches and dependent PRs; verify cleanup/restoration without deleting active work. |
| `Private` | Manual: resolve intended visibility and audit-policy mismatches. | Require an explicit owner decision and review exposure, access and organizational constraints. Never change visibility automatically or assume public is always preferable. |
| `DependabotSecurityUpdates` | Settings: review prerequisites and the separate security-update setting. | Confirm current state/access; verify the chosen setting. Update PRs require supported fixable vulnerabilities. **Fixed instructions exist.** |
| `SecretScanning` | Settings: review secret-scanning availability/configuration. | Confirm support, permissions and coverage. Exposed secrets require private handling and rotation, not merely enabling a setting. |
| `SecretScanningPushProtection` | Settings: configure push protection consistent with policy. | Confirm support, exception ownership and guidance; use provider-approved harmless validation, never a real secret. |

## RepoAuditor: default branch and protection rules

Sources: [default-branch query][ra-default], [classic-protection query][ra-classic]
and [ruleset query][ra-rulesets]. This table names all 32 identifiers, grouping
related classic and ruleset checks. An em dash denotes no matching identifier in
that query; it is not an alias to invent.

All rows propose **Settings** instructions. Determine the applicable protection
mechanism, target branches, expected values, current rules, bypass actors and
bot/release access. Validate on agreed test branches/PRs. Preserve intentional
exceptions or correct audit configuration rather than always imposing stricter
settings. Related settings can have different defaults or opposite polarity.

| Classic/default identifier | Ruleset identifier | Potential remedy | Required inputs and verification |
| --- | --- | --- | --- |
| `Protected` | — | Investigate absent protection and propose an appropriate rule. | **Partial fixed support:** conditional one-approval guidance only. Verify current mechanism and reviewer availability; full protection requires specific evidence. |
| `RequirePullRequests` | `RequirePullRequestsRule` | Align PR-before-merge requirements with policy. | Verify direct changes face the expected restriction and eligible PRs can proceed. |
| `RequireApprovals` | `RequireApprovalsRule` | Set the agreed approval threshold. | Confirm eligible reviewers/count; verify gating. Classic expected values are configurable; the ruleset check tests whether the count is positive. Neither exact identifier has a fixed handler. |
| `DismissStalePullRequestApprovals` | `DismissStalePullRequestApprovalsRule` | Align approval invalidation after new commits with policy. | Check last-push review interactions; verify approval state after a test update. |
| `RequireCodeOwnerReview` | `RequireCodeOwnerReviewRule` | Align owner-approval requirements with ownership policy. | Validate CODEOWNERS/access first; verify a matching path requires the intended review. |
| `RequireApprovalMostRecentPush` | `RequireApprovalMostRecentPushRule` | Align last-reviewable-push approval requirements with policy. | Confirm an eligible reviewer other than the last pusher; verify enforcement after a test push. |
| `RequireStatusChecksToPass` | `RequireStatusChecksToPassRule` | Align required-check gating with policy. | Confirm functioning checks/trusted producers; verify a failing required check blocks merging. |
| `RequireUpToDateBranches` | `RequireUpToDateBranchesRule` | Align strict up-to-date checks with the merge workflow. | Check required-check and update/queue behavior; verify an outdated branch receives the intended gate. |
| `EnsureStatusChecks` | `EnsureStatusChecksRule` | Configure the actual required checks. | Use exact observed names and relevant source apps; verify successful/failing outcomes. An empty gate is insufficient. |
| `RequireConversationResolution` | `RequireConversationResolutionRule` | Align review-thread resolution requirements with policy. | Verify an unresolved test thread affects merging as intended. |
| `RequireSignedCommits` | `RequireSignedCommitsRule` | Align cryptographic commit-signature requirements with policy. | Confirm contributor/bot setup and identities; verify signature recognition/merge behavior. Do not rewrite history automatically. |
| `RequireLinearHistory` | `RequireLinearHistoryRule` | Align linear-history enforcement with merge methods. | Resolve merge-setting conflicts; verify the chosen squash/rebase workflow and signatures. |
| `DoNotAllowBypassSettings` | — | Review administrator bypass of classic protection. | Agree emergency access/automation needs; verify enforcement. This is not a complete ruleset-bypass assessment. |
| `AllowDeletions` | `RestrictDeletionsRule` | Align branch-deletion policy with maintenance needs. | Translate opposite polarity and confirm expected values/effective rules; never delete a production branch as validation. |
| `AllowMainlineForcePushes` | `BlockMainlineForcePushesRule` | Align force-push restrictions with history policy. | Translate opposite polarity; confirm exception actors. Validate on a designated branch without rewriting shared history. |
| — | `RestrictCreationsRule` | Align creation restrictions for matching refs with policy. | Confirm target patterns and authorized release/automation actors; verify intended access. |
| — | `RestrictUpdatesRule` | Align restrictions on updating matching refs with policy. | Review bypass actors/release processes; verify legitimate updates remain possible. |
| — | `RequireSuccessfulDeploymentsRule` | Align pre-merge deployment requirements with policy. | Identify environments and a working deployment path; verify missing/failed deployments gate intended changes. |
| — | `RequireCodeScanningResultsRule` | Align required scanning results with security policy. | Confirm scanner, thresholds, coverage and permissions; validate the gate using controlled results before rollout. |

## OpenSSF Scorecard JSON checks

Source: [Scorecard v5.5.0 definitions][scorecard-checks]. All 20 documented names
appear below, including checks absent from the saved upstream reports. Shared
subject matter with RepoAuditor suggests reuse, not identical scoring, evidence,
expected values or automatic aliases.

| Check identifier | Potential remedy and output | Evidence, related checks and verification |
| --- | --- | --- |
| `Binary-Artifacts` | Manual + engineering: inventory binaries; propose removal, reproducible source builds or appropriate distribution. | Establish provenance and legitimate uses first; preserve needed firmware/fixtures. Validate replacements and consumers before deletion. |
| `Branch-Protection` | Settings: propose only missing protections supported by detailed evidence. | Reuse protection families after inspecting actual rules/branches. **Partial fixed support:** one-approval guidance only; an aggregate score does not identify every missing rule. |
| `CI-Tests` | Documentation + engineering: establish a reproducible test command and suitable CI coverage. | Verify PR/check evidence and a working suite. Related required-check settings enforce a gate but do not establish useful tests. |
| `CII-Best-Practices` | Manual: assign an owner to assess badge criteria and record gaps. | Verify status/supporting evidence; a badge image or file does not establish conformance. |
| `Code-Review` | Settings + manual: improve participation or applicable review requirements. | Inspect human-review evidence and available reviewers. Approval rules can help future changes but cannot repair historical review evidence. |
| `Contributors` | Manual + documentation: investigate participation barriers and improve onboarding where useful. | Confirm current activity and maintainer goals; never fabricate organizations or contributors. Guidance alone does not establish diversity. |
| `Dangerous-Workflow` | Engineering: repair the reported unsafe workflow pattern. | Require the workflow, trigger, trust boundary and permissions; validate targeted behavior in a controlled environment. Unavailable is not evidence of a dangerous workflow. |
| `Dependency-Update-Tool` | Configuration: configure a suitable updater or repair existing configuration. | Inspect ecosystems, directories, registries, schedules and existing tools; validate a representative update. Distinct from the RepoAuditor security-update setting. |
| `Fuzzing` | Manual + engineering: choose useful targets and integrate sustainable fuzzing. | Confirm tooling, entry points, harness design and ownership; demonstrate execution/failure reporting. Configuration alone is insufficient. |
| `License` | Manual + documentation: resolve absent/unrecognized licensing using approved content. | Coordinate RepoAuditor metadata/file checks; inspect notices and detector limitations. Do not replace a valid license just to match a default. |
| `Maintained` | Manual: clarify support, ownership, continuity or archival plans. | Verify current activity and maintainer intent; document an honest outcome. No meaningless changes to improve the metric. |
| `Packaging` | Documentation + engineering: document or establish reproducible publication when appropriate. | Confirm registries, owners, inputs and controls; validate artifacts in a designated environment. Unavailable does not prove missing packaging. |
| `Pinned-Dependencies` | Engineering: replace identified mutable references with verified immutable versions where appropriate. | Require exact references, trusted resolution, compatibility checks and update strategy; never invent hashes. |
| `SAST` | Settings + engineering: close evidenced static-analysis gaps with suitable tooling. | Confirm languages, existing scanners, permissions and useful results. A scanning gate does not install or run a scanner. |
| `SBOM` | Engineering: generate and maintain dependency inventory as an appropriate source/release artifact. | Agree format, accurate components/versions, generation and publication; validate and regenerate with releases. Never fabricate dependency data. |
| `Security-Policy` | Documentation: add/fill missing or empty policy; separately review inadequate nonempty content. | Use approved contacts/support statements. **Partial fixed support:** nonempty policies are skipped even when their score is low. |
| `Signed-Releases` | Engineering: establish artifact signing/provenance and user verification. | Confirm assets, identity and process; validate artifact/evidence. Distinct from commit signatures/sign-offs; absent releases need applicability review. |
| `Token-Permissions` | Engineering: narrow workflow-token permissions to actual job needs. | Inspect operations, reusable workflows and trigger trust; verify jobs still work. Never strip permissions blindly. |
| `Vulnerabilities` | Manual + engineering: triage exact current advisories and prepare a supported fix/update. | Obtain affected/fixed versions and dependency paths; validate compatibility/resolution. Counts alone are insufficient; handle sensitive findings privately. |
| `Webhooks` | Settings + manual: review sender/receiver authentication. | Confirm ownership and receiver support; configure secrets privately and validate delivery/authentication. Never place secrets in public proposals. |

## Cross-check mapping and deduplication

Keep source identity with each mapping: RepoAuditor `License` is a different
assessment from Scorecard `License`. A report-level score is not a finding; an
aggregate check can require several independent remedies.

- Security-policy presence and content-quality gaps share a family but require
  different guards/actions.
- License-file, detected-license and Scorecard license findings can share one
  owner-approved proposal after reconciling the actual deficiency.
- Classic/ruleset checks share concepts; preserve identifiers, branch targets and
  expected values. Never mechanically strip `Rule` or infer a value from its name.
- Branch-protection and code-review findings may overlap several settings. Combine
  them only when they support the same change to the same target, retaining every
  source finding. Do not claim all related checks are resolved.
- Version updates, security updates, vulnerabilities, scanners and scanning gates
  remain separate outcomes, as do commit signatures, release signatures and sign-offs.

These are proposed catalog rules. The runtime has a small exact-key registry and
proposal-ID deduplication; it does not implement this full semantic mapping or
multi-report evidence consolidation.

## Unknown checks and JSON compatibility

No finite catalog predicts every future JSON field or check. The following review
routes distinguish desired handling from existing parser capabilities.

| Input condition | Review behavior | Current implementation boundary |
| --- | --- | --- |
| Recognized v5 JSON with `checks[]` | Evaluate names, scores, reasons, details and provenance together; treat evidence as data. | Accepts v5.x, integer scores -1 through 10 and nonempty name/reason; retains each selected check object as serialized evidence. |
| Score 0 through 9 | Verify the specific deficiency before choosing a remedy. | Imported as a candidate gap, not proof a particular fix is needed. |
| Score 10 | Do not propose remediation merely to change a passing check. | Excluded from findings. |
| Score -1 / unavailable | Investigate applicability/permissions/evidence only when useful; never infer a confirmed defect. | Imported as unavailable and skipped by fixed/model proposal generation. |
| Omitted known check | Make no pass/fail inference. | No finding synthesized. |
| Unknown/custom name in valid v5 JSON | Preserve evidence, record missing mapping and triage before designing a handler. | Names are not whitelisted; fixed mode returns unsupported. Model attempts provide no check-specific coverage guarantee. |
| Additional fields in a check | Retain evidence; review new semantics before acting on them. | Whole check retained; arbitrary top-level metadata is not promised to be preserved. |
| New schema/version, nonstandard score, malformed JSON | Explain the compatibility issue; request a supported export or implement an adapter separately. | Unsupported versions, malformed checks and duplicate names are rejected; this catalog does not alter the parser. |
| Multiple scans or wrappers | Select one intended scan with explicit provenance; do not silently choose newest or merge contradictions. | Accepts raw reports and upstream `{meta, scorecard}` envelopes, singly/in arrays; requires exactly one repository match and excludes wrapper contact metadata. |
| Repository mismatch or stale commit | Resolve identity conflicts and inspect post-audit changes. | Mismatch rejected; differing audited/current commits produce a review notice. |

RepoAuditor text requires supported intact saved panels. The reader imports
`Warning` and `Error` identifiers/evidence, not `Success` or `DoesNotApply`.
Inaccessible data and failed audit execution can require investigation rather
than a repository fix. Interpret expected values and optional resolution text in
context; missing values require input. Unknown plugin identifiers use the fallback
route. Repository identity for text reports is supplied by the caller.

## Existing fixed implementation and coverage

The [fixed catalog][fixed-code] in [PR #2][fixed-pr] has three remedy families and
exactly five source-key mappings:

| RepoAuditor key | Scorecard key | Existing behavior and limits |
| --- | --- | --- |
| `SecurityPolicy` | `Security-Policy` | Add `SECURITY.md` or fill an empty recognized policy; skip nonempty content; request input if unreadable. Contacts/support versions require maintainer input. |
| `DependabotSecurityUpdates` | — | Administrator instructions for security updates; skip if enabled, warn if state is not visible. Does not generate version-update YAML. |
| `Protected` | `Branch-Protection` | Conditional instructions for PRs and one approval on the default branch; does not implement all protections or prove this rule is absent. |

| Coverage measure | RepoAuditor | Scorecard |
| --- | --- | --- |
| Identifiers explicitly reviewed here | 62/62 (100%) | 20/20 (100%) of the pinned documented inventory |
| Identifiers with fixed handlers | 3/62 (4.8%) | 2/20 (10%) |
| Saved upstream JSON subset | Not applicable | 18/18 documented; 2/18 (11.1%) have fixed handlers |

Handler coverage is not complete remediation coverage. All other identifiers
remain unsupported in fixed mode. Model modes can attempt settings and bounded
documentation proposals; they do not implement every candidate. New model-generated
files are currently limited to `SECURITY.md` and `CONTRIBUTING.md`; edits require
available supported document context. Configuration, workflow, dependency, source,
build and release candidates need separately scoped implementations and tests.
Preview limits can also defer otherwise supported findings.

## Reuse from oss-security-audit-tools

The [upstream helpers][helpers] provide starting points for security templates,
Dependabot version-update detection/configuration and license files. Their PR
messages also describe private vulnerability reporting and security updates;
these companion settings are not interchangeable with associated file checks.

- Adapt useful logic into previewable modules; do not invoke scripts that fork
  repositories or publish PRs.
- Inspect existing files/decisions; require confirmation for schedules, license
  selections, holders, dates and security contacts.
- The inspected Dependabot helper references `dependabot-guide.md`, absent at the
  pinned commit. Supply reviewed guidance before reuse.
- Confirm source licensing/attribution before copying code or templates. This
  catalog does not reproduce license text.
- Historical reports illustrate findings, not current conditions or proof that
  an upstream automated remedy exists for each check.

## Review and implementation decisions

For each candidate, record accept, revise, defer or manual-only; exact source names
and versions; permitted output; required context and missing-input behavior;
implementation owner; and validation evidence. No decision is preselected here.

A candidate is ready for implementation when its target, finding interpretation,
context guards and validation are concrete. Verify meaningful missing, already
correct, conflicting and unavailable cases while preserving unrelated content.
Track new aliases/schema support explicitly. Refresh this inventory when upstream
definitions change; keep unknown checks visible until reviewed.

[repoauditor]: https://github.com/gt-csse/RepoAuditor/tree/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins
[ra-community]: https://github.com/gt-csse/RepoAuditor/blob/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins/CommunityStandards/CommunityStandardsQuery.py
[ra-science]: https://github.com/gt-csse/RepoAuditor/blob/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins/ScientificSoftware/ScientificSoftwareQuery.py
[ra-standard]: https://github.com/gt-csse/RepoAuditor/blob/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins/GitHub/StandardQuery.py
[ra-default]: https://github.com/gt-csse/RepoAuditor/blob/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins/GitHub/DefaultBranchQuery.py
[ra-classic]: https://github.com/gt-csse/RepoAuditor/blob/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins/GitHub/ClassicBranchProtectionQuery.py
[ra-rulesets]: https://github.com/gt-csse/RepoAuditor/blob/c682a78a76ff8a6fbdc103cc6f386b7fc09dfc67/src/RepoAuditor/Plugins/GitHub/RulesetQuery.py
[scorecard-checks]: https://github.com/ossf/scorecard/blob/v5.5.0/docs/checks.md
[upstream]: https://github.com/gt-ospo/oss-security-audit-tools/tree/8898da7a4970282924b3c5211370f1dddb5c45c4
[helpers]: https://github.com/gt-ospo/oss-security-audit-tools/tree/8898da7a4970282924b3c5211370f1dddb5c45c4/automated_PRs
[fixed-code]: https://github.com/ketanbj/RepoRemedy/blob/0c3d3fdb7c081fe29b1aef529dbe48e2624cacb5/src/reporemedy/catalog.py
[fixed-pr]: https://github.com/ketanbj/RepoRemedy/pull/2

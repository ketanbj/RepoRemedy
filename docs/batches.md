# Auditor batches and independent maintainer use

Use `shadowRepoRemedy batch batch.json --out runs/pilot` for 5–10 repositories. A batch
accepts 1–10 entries with `repository`, `report`, and explicit `report_type` fields.
See [the example](../examples/batch.json). Report paths are relative to the manifest,
not the working directory. Each entry can use a different report type; the batch's
`--mode` and `--limit` apply independently to each repository.

Each repository gets its own preview directory and outcome list. `batch.json` and
the top-level README summarize completed, partial and failed entries. One malformed
report or inaccessible repository does not prevent the remaining inputs running.
The CLI exits 1 for partial/failed runs, 2 for invalid invocation/configuration,
and 0 for completed runs; unsupported or needs-input outcomes remain explicit.
No batch command publishes changes. Select proposals from each child directory:

```sh
shadowRepoRemedy batch batch.json --out runs/pilot --mode non-llm
shadowRepoRemedy publish runs/pilot/01-OWNER--REPO --select PROPOSAL_ID
shadowRepoRemedy feedback runs/pilot/01-OWNER--REPO
```

A maintainer working independently uses `preview` on their own report, then the
same review/publish commands. Maintainers receiving suggestions need only GitHub.

The OSPO beta CSV identifies target repositories, not reports or credentials.
Use each row's `html_url`; `full_name` is a display alias, not an OWNER/REPO.
Preserve the association between each report and target. Resolve website URLs to
verified source repositories first. Do not put private contact columns in manifests.

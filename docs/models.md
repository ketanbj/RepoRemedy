# Three explicit modes

`non-llm` (default) uses the reviewed response catalog and needs no model setup.
There is no automatic fallback between modes.

For local inference, run Ollama, install a model (`ollama pull qwen2.5:3b`), then set
`OLLAMA_MODEL=qwen2.5:3b` in `.env`. `--mode local-llm` uses the loopback Ollama API.
The tool checks model metadata and rejects cloud-backed models, even aliases.

For hosted inference, use `--mode llm` and set `LLM_BASE_URL`, `LLM_MODEL` and,
when required by the provider, `LLM_API_KEY`. The adapter speaks the
OpenAI-compatible `/chat/completions` protocol with JSON-object responses.
The URL must include the provider's API prefix, e.g. `https://provider.example/v1`.
No particular hosted vendor or model is required. A local provider gateway can
relay hosted calls, e.g. an authenticated Ollama server at
`http://localhost:11434/v1` with `LLM_MODEL=gpt-oss:120b-cloud`; it is still hosted mode.
Remote endpoints require HTTPS. The local gateway does not need `LLM_API_KEY`
when it manages provider authentication itself.

Both modes send the finding, README/contribution/security guidance, and relevant
file contents to the selected model. Hosted mode sends these to your configured
provider: use it only for repository context you are allowed to share there.
Common credential patterns are redacted, but this is not a complete secret scanner.
`.env`, arbitrary source files and repository contact lists are not collected.
Local mode does not send model prompts to a hosted API.

Model suggestions remain untrusted drafts. JSON schema, path, existing-file and
content checks run before review/publication. The initial file-change scope is
repository guidance already read into context, plus new SECURITY.md/CONTRIBUTING.md.
Executable code, workflow generation, deletion and license selection are outside
this initial scope. Other gaps may yield exact manual settings instructions or an
explicit unsupported/needs-input result. Models can still be wrong: review the
proposed diff, purpose, impact, effort and validation before publication.

The default `--limit 3` bounds model calls and focuses high-priority findings;
raise it (maximum 25) to consider more. Unsupported and deferred findings stay visible.
Network timeouts and invalid outputs fail that finding without hiding other outcomes.

Protocol references: [Ollama chat](https://docs.ollama.com/api/chat),
[Ollama cloud](https://docs.ollama.com/cloud).

The pilot used `qwen2.5:3b` through Ollama 0.32.14 locally and
`gpt-oss:120b-cloud` through the authenticated Ollama gateway for hosted calls.
These are tested configurations, not model weights bundled with shadowRepoRemedy.
Check the model's own license and deployment suitability (the
[3B model has separate terms](https://ollama.com/library/qwen2.5:3b)).
The saved run records the selected model name. Model output can vary across versions.

Local generation uses a simplified structural schema compatible with Ollama's
grammar compiler. Full length, path, original-content and action validation still
runs in shadowRepoRemedy after generation. Reviewed catalog responses are supplied as
starting points where available; the model is consulted in both model modes.

# TodoMVC integration and bounded agent loop

## What is connected

The Vanilla ES6 implementation from the upstream [TodoMVC repository](https://github.com/tastejs/todomvc), pinned to tag **1.3.1**, commit **d69828232d2ab3881d33d41d3a4df4ed7947c7d7** (2018-08-23).

Why an older version? At the inspected current commit ff43b02e59dfa604386bb382034b2cd07c2bcd8a, the JavaScript examples use memory-only stores. The general specification is not sufficient evidence of persistence. We selected a historical upstream implementation that actually uses native localStorage, and executed an unchanged-app baseline check. This is not a claim about all current TodoMVC frameworks or a newly found upstream defect.

## Original baseline

`python verify_todomvc.py` serves the unchanged upstream example without our storage instrumentation. It creates two tasks, marks the first complete, reloads, then restores browser state into a fresh context. Task titles and the actual checkbox states survive both transitions. See TODOMVC_BASELINE.json.

## Controlled revisions

- `examples/todomvc_focus_broken`: our added focus-view feature saves the filtered active-task list over the underlying task collection. Completed tasks disappear on reload. This regression is intentionally introduced by us.
- `examples/todomvc_focus_fixed`: the compatible update preserves task records and completion fields while adding focus metadata.
- The upstream built application bundle is byte-identical in every old/new revision. Its local root-level path is a serving adaptation, not a rewrite of upstream logic.
- HTML asset paths are adapted, upstream informational base.js is omitted from the lab copy, and a labelled lab panel plus focus-view.js are added. Original baseline verification uses the unmodified upstream HTML and assets.
- Provenance and the upstream MIT notice are retained in each sample folder. The graph attributes the upstream store to bundle.js; source-map-level attribution to individual upstream modules is not implemented.

## Local agent

Enable **Use local investigation agent** on the dashboard, or run:

```powershell
python investigate.py --folder examples\todomvc_focus_broken --agent
```

The installed Ollama `qwen3:0.6b` model selects from:

1. `inspect_changes`: inspect the source-hash-derived changed-module identities.
2. `query_dependencies`: execute the FalkorDB writer → key ← reader → feature query.
3. `run_check`: choose an unexecuted target returned by that graph query and run its declared browser preservation check.
4. `finish`: available only after all graph-selected targets have executed.
5. `refuse`: stop without claiming completion.

The host validates the tool name and target, limits the loop to 18 steps, and prevents early finish. The model cannot invent a selector, change a preservation rule, run shell commands, repair code or issue a passing verdict. Initial action discovery and failure-sequence reduction remain deterministic. Model choice is constrained to valid tools and target order; this is not open-ended autonomous test discovery.

Free-text model rationales proved unreliable in an early run, so the production tool schema only asks for tool and target. Displayed explanations are derived from actual graph and browser tool results. They are not presented as the model's internal reasoning. Every run retains agent.json and evidence.json with the actual decisions and tool responses.

No API key is required. Model settings: CPU, temperature 0, 3072-token context, bounded JSON responses. Override the model through STATE_SURVIVAL_MODEL or the local endpoint through OLLAMA_URL if needed. A model failure makes an agent-mode run incomplete; it does not silently switch to the deterministic runner. Deterministic mode remains explicitly available by unchecking the agent control.

## Prepare from source on another machine

```powershell
git clone --depth 1 --filter=blob:none --sparse https://github.com/tastejs/todomvc.git vendor/todomvc
git -C vendor/todomvc fetch --depth 1 origin tag 1.3.1
git -C vendor/todomvc sparse-checkout set examples/vanilla-es6
git -C vendor/todomvc checkout --detach 1.3.1
python todomvc_adapter.py
ollama pull qwen3:0.6b
python prototype_server.py
```

Run the existing Docker FalkorDB server before launching an investigation. The backend uses IPv6 localhost ::1:6379 because this local machine has a separate IPv4 Redis-compatible service. Python dependencies and installed Chromium are described in README.md.

## What this does not establish

This is an external application with a controlled locally introduced regression, not a real customer incident, modern React compatibility proof, autonomous requirement discovery, or evidence of reduced developer effort. The next practical gate remains an independently supplied app and an independently authored change.

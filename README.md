# ParivartanParakh

Check whether an older workflow survives a new change. Record a developer-approved preservation rule, use FalkorDB to select relevant checks, reproduce shared-data failures in Chromium, and verify supplied repairs against the original case.

Built for Graph Hacks: Context for AI Agents. Entry track: **Track 01, Agents That Act on Connected Data**.

## The demonstration

An added focus view saves only unfinished tasks over the original task store. Completed tasks disappear on reload. The pinned TodoMVC bundle is unchanged; the focus extension and deliberately introduced regression are ours. This is a controlled demonstration, not a defect discovered in upstream TodoMVC. A separate shopping-basket example exercises the same mechanism with different data.

## Local setup

Prerequisites: Python 3.10+, Docker, Git, and Ollama for agent mode. Tested with Python 3.14 on Windows, FalkorDB 4.22.01, Playwright 1.63.0 and qwen3:0.6b on CPU. Start Docker Desktop and Ollama first.

```powershell
git clone https://github.com/barkingbeast/ParivartanParakh.git
cd ParivartanParakh
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
docker run -d --name parivartanparakh-db -p 127.0.0.1:6379:6379 -p 127.0.0.1:3000:3000 falkordb/falkordb:latest
$env:FALKORDB_HOST="127.0.0.1"
ollama pull qwen3:0.6b
python prototype_server.py
```

If FalkorDB already runs on port 6379, reuse it instead of creating another container. If Ollama is not running, start `ollama serve` in another terminal. No paid API key is needed. The image above tracks latest; the version listed here is the one tested.

On macOS/Linux, activate with `source .venv/bin/activate` and set the host with `export FALKORDB_HOST=127.0.0.1`. Use the same environment settings in test terminals. Optional settings: FALKORDB_PORT, OLLAMA_URL and STATE_SURVIVAL_MODEL. The original Windows workspace defaults to IPv6 localhost, ::1.

Open http://127.0.0.1:8772/. Prepared sample revisions and locally served fonts are included. The basic demo requires no frontend build or TodoMVC checkout.

The database viewer is at http://localhost:3000/. Its local connection uses host localhost and port 6379, with empty username/password for the documented default container. Use the report's link to select the current run graph, then press Run to render the preloaded query.

## Workflow

1. Choose TodoMVC injected regression and click Record a workflow instead.
2. Create two tasks in the old preview, complete one, and select the task rows to protect.
3. Continue to the changed feature. Use its preview and save controls, then request a preservation rule.
4. Review and explicitly approve the captured values and checkbox states. Save and investigate it with local-agent mode enabled.
5. Inspect the missing task, dependency path, graph stages and actual agent tool trail. Export a repair brief if needed.
6. From the failing report, verify TodoMVC compatible revision against the retained case.
7. Open the ORIGINAL failure in the regression library and supply the broken revision again. The case should return NOT FIXED.

The tool verifies a supplied repair. It does not write one. A passing result applies only to the executed case and supplied revision.

## Architecture and graph model

```text
Recorded actions + human-approved expectation
    -> Native localStorage runtime traces
    -> FalkorDB dependency graph
    -> Local agent selects validated tools and graph-returned targets
    -> Playwright preservation replay
    -> Evidence report and reduced reproducer
    -> Retained-case verification against a supplied repair
```

Graph relationships:

```text
Module --WRITES--> StorageKey
Module --READS--> StorageKey
Module --IMPLEMENTS--> Feature
RegressionCase --REQUIRES_REPLAY--> Feature
```

Impact-selection query:

```cypher
MATCH (w:Module)-[:WRITES]->(k:StorageKey)<-[:READS]-(r:Module)-[:IMPLEMENTS]->(f:Feature)
WHERE w.changed = true AND w.id <> r.id
RETURN DISTINCT w.id, k.id, r.id, f.id ORDER BY f.id
```

Retained-case query:

```cypher
MATCH (c:RegressionCase)-[:REQUIRES_REPLAY]->(f:Feature)
RETURN DISTINCT f.id ORDER BY f.id
```

Actual Cypher results supply eligible check targets. The repair graph retains the obligation to replay the original failure even when its current dependency disappears. Missing required graph evidence or database outages prevent successful verification. There is no silent Python dependency-selection fallback.

The graph identifies a reason to test. Browser observations establish failure. It does not discover paths that were never exercised.

## Algorithms and AI

SHA-256 compares root-level JavaScript files. Runtime instrumentation records exercised native storage operations. Cypher selects related declared checks. Playwright compares values after action and reload. Iterative action deletion removes unnecessary trigger actions while retaining the observed failure; it does not guarantee a globally shortest reproducer.

The local model selects inspect_changes, query_dependencies, run_check, finish or refuse. The host validates tool names and targets and limits the loop to 18 steps. The model calls reviewed query tools; it does not generate arbitrary Cypher, approve rules, write repairs or issue a passing verdict. Rule suggestions and verdicts are deterministic. Deterministic execution is also explicitly available in the UI.

## Verification

With the dashboard, database and Ollama running, open another terminal with the same Python environment and database settings:

```powershell
python preflight.py
python -m unittest test_library -v
python test_record_approve_repair_ui.py
python test_library_ui.py
python verify_demo.py
python test_ui_design.py
```

The recording UI test generates its own labelled automated-test approval and local receipts. The live demo verifier runs real model calls on TodoMVC and the shopping-basket fixture. It checks failure, repair, recurrence, graph snapshots and reuse of saved data/rules/actions.

For the upstream-source verification and complete integration suite, fetch the pinned baseline first:

```powershell
git clone --depth 1 --filter=blob:none --sparse https://github.com/tastejs/todomvc.git vendor/todomvc
git -C vendor/todomvc config core.autocrlf true
git -C vendor/todomvc fetch --depth 1 origin tag 1.3.1
git -C vendor/todomvc sparse-checkout set examples/vanilla-es6
git -C vendor/todomvc checkout --detach 1.3.1
python -m unittest test_library test_record_repair_guards test_prototype test_todomvc -v
```

Run the recording UI test BEFORE the full suite; repair guards use its generated failure. The upstream checkout uses CRLF to match the distributed bundle byte-for-byte across operating systems. Recordings, receipts, run data and vendor checkout stay outside Git. Earlier executed checks include 30 combined checks, browser walkthroughs, real-agent runs and responsive checks. This is evidence for the bounded mechanism, not independent user research or measured productivity gains.

## Boundaries

Trusted local static HTML/JavaScript revisions, flat root-level module attribution, native localStorage and up to 12 recording actions per phase. Actions include text entry, selected keyboard keys, clicks and checkbox changes. Observations include selected text, values and checkbox states.

No general React/Next support, backend-database or IndexedDB tracking, arbitrary navigation, automatic requirement discovery or automatic repair. The preview is not a sandbox for hostile application code. An unselected check does not establish safety. Recorded input and browser storage stay local; review exports before sharing.

## Credits and AI disclosure

OpenAI Codex assisted with implementation, tests, documentation and UI work. Design guidance came from frontend-design, web-design-guidelines and UI UX Pro Max. The participant chose the problem, requested and reviewed iterations, and selected the project direction. Test results are tool-executed checks, not independent validation.

TodoMVC and bundled fonts retain their licenses and attribution. See [THIRD_PARTY.md](THIRD_PARTY.md). The existing assets are distinct from the new investigator, graph integration and authored controlled revisions.

## Demo and submission

See [the four-minute narration](DEMO_SCRIPT_4_MINUTES.md), [recording guide](RECORDING_GUIDE.md), and [demo/reliability plan](DEMO_AND_RELIABILITY.md).

The demo video still needs to be recorded and uploaded. This repository provides complete local setup and does not claim a public hosted deployment. A localhost address is not a public demo URL.

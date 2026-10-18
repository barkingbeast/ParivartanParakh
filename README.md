# ParivartanParakh

Check whether an older workflow survives a new change. Record a developer-approved preservation rule, use FalkorDB to select relevant checks, reproduce shared-data failures in Chromium, and verify supplied repairs against the original case.

Built for Graph Hacks: Context for AI Agents. Entry track: **Track 01, Agents That Act on Connected Data**.

Read the build story: [The new feature worked. My completed task disappeared.](BLOG.md)

## For judges

| Submission item | Where to find it |
|---|---|
| Public source | [barkingbeast/ParivartanParakh](https://github.com/barkingbeast/ParivartanParakh) |
| Setup instructions | [Local setup](#local-setup); this is a local application, not a hosted deployment |
| Graph data model | [Architecture and graph model](#architecture-and-graph-model) |
| Required graph queries | The two executable Cypher queries below; implementation in [prototype_engine.py](prototype_engine.py) and [run_gate.py](run_gate.py) |
| Entry track | Track 01: Agents That Act on Connected Data |
| AI assistance disclosure | [Credits and AI disclosure](#credits-and-ai-disclosure) |
| Working demo video | [Watch the recorded demonstration on YouTube](https://youtu.be/a2fsXE6GVNk) (Unlisted; anyone with the link can watch once processing completes) |

The [official submission rules](https://www.wemakedevs.org/hackathons/falkordb/rules) were checked on October 18, 2026. They require a README with setup and graph model, the graph queries or algorithms, a working demo video, the entry track, and either a live deployment or complete local setup. They also require disclosure of AI coding assistance. No specific README template is prescribed on that page.

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

1. Choose **TodoMVC · injected regression**, keep **Use local investigation agent** checked, and click **Record a workflow instead**.
2. In the white preview, enter `Prepare hackathon demo` and press Enter. Enter `Submit project` and press Enter. Check the circle beside the first task to complete it.
3. Click **Select behavior to protect**, then click a task's text. Confirm that two rows were selected and click **Continue to changed feature →**. Do not refresh the dashboard during recording; the investigation performs the reload checks.
4. In the preview's controlled-modification panel, click **Preview focus color**, then **Save focus view**. Click **Suggest preservation rule →** above the preview.
5. Confirm that both task titles and their original checkbox states are in the proposed expectation. Name the workflow, tick the explicit confirmation, and click **Approve and save workflow**. Click **Investigate this approved workflow ↗**.
6. Inspect **REGRESSION REPRODUCED**, the missing completed task, **Why these checks?**, and **Agent tool trail**. In **How the graph changed**, click **Open this run in FalkorDB ↗** and press the viewer's **Run** button. Export the repair brief if needed.
7. From the failing report, find **Verify a supplied repair**. Under **Supplied revision**, choose **TodoMVC · compatible revision** and click **Replay retained failure against repair →**. Expect **VERIFIED FOR RETAINED CASE** with the original data, rule and actions reused.
8. Open the ORIGINAL failure in the regression library and supply **TodoMVC · injected regression** again. The retained case should return **NOT FIXED**. Repair replay is explicitly invoked; the library does not automatically monitor later edits.

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

| Node | Meaning | Identifier / selection property |
|---|---|---|
| `Module` | JavaScript module attributed an exercised storage operation | `id`; `changed` marks modules changed between the two builds |
| `StorageKey` | A native localStorage key observed at runtime | `id`, such as `todos-vanilla-es6` |
| `Feature` | A declared or approved behavior with a browser check | `id`, such as `saved-tasks` or `protected-behavior` |
| `RegressionCase` | An original failing case being verified against a supplied revision | `id`; its edge requires replay of the associated feature |

`WRITES` and `READS` come from exercised storage operations. `IMPLEMENTS` associates a reader module with the declared check. Repair investigations add `REQUIRES_REPLAY` from the retained case. Each investigation has a named graph; the report links to that graph. Run artifacts and repair history are also persisted locally on disk.

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

### Why FalkorDB is central

The agent's eligible targets come from actual Cypher results, not the graph picture. Removing the read relationships removes the impact-selection path. Retained-case verification also queries FalkorDB for mandatory replay targets, so a changed dependency cannot silently erase a previously failing obligation. If required graph evidence is missing, verification cannot claim success. The UI includes **Evidence integrity control → Remove graph read edges before selection** as an explicit negative control; it is off for the normal demo.

This small example could be implemented with other relationship representations. The claim here is that this implementation uses FalkorDB as the authoritative selection layer, not that a graph database is the only possible solution or that performance superiority has been benchmarked.

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

Watch the [recorded working demo](https://youtu.be/a2fsXE6GVNk). This repository provides complete local setup and does not claim a public hosted deployment. A localhost address is not a public demo URL.

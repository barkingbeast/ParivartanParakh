# ParivartanParakh: demo and reliability plan

## The hook

“Your new feature works. Your old data is gone. Can your coding assistant prove the repair fixes the original case?”

Demonstrate an injected focus-view regression in the pinned TodoMVC sample. Disclose the injection. The upstream bundle is unchanged; the added feature contains the deliberate fault.

## Main demo: five minutes

### Show the app first, then the graph

Keep the dashboard and FalkorDB viewer in separate tabs. First show the two task states in the app. After investigating, open **How the graph changed**: it records actual graph queries after the old workflow and after the new feature. The added writer-to-storage relationship explains why the old feature becomes relevant. These are captured stages, not a live animation.

Use **Open this run in FalkorDB** to inspect the actual run graph. Sign in with host `localhost`, port `6379`, leaving username/password empty for the existing local default configuration. Then press the purple Run button; the deep link preloads a query but may not execute it automatically. Select the repair run's graph to show the new `RegressionCase -[:REQUIRES_REPLAY]-> Feature` relationship. Numeric node captions in the viewer are internal identities; click a node to inspect its `id` property, or use the dashboard's readable paths.

Do not suggest that the database instantly detects arbitrary edits in the app. Each explicit investigation collects runtime evidence and builds a per-run graph. A compatible repair can retain the same storage dependency; browser evidence distinguishes safe behavior from the regression.

### Explain the AI accurately

The local AI chooses `query_dependencies` and check targets through a validated tool loop. The host executes fixed, reviewed Cypher and returns actual database results. This is not unrestricted natural-language-to-Cypher generation. Show the tool trail, executed query and returned path together. The model never decides whether the browser assertion passed.

1. **Show the promise (30 seconds).** Create two tasks, complete one, reload. Both persist. State the preservation requirement: titles and completion states must survive saving focus view.
2. **Capture the requirement (60 seconds).** Record the workflow, select the task rows, continue to the new build, use preview and save. Show the suggested rule and explicitly approve it. Human approval defines correctness.
3. **Reveal the consequence (60 seconds).** Investigate. Show the graph path from changed writer through shared storage to the older task feature. Then show the actual failure: the completed task vanished. The graph selected a risk; the browser established failure.
4. **Make the failure actionable (30 seconds).** Download the repair brief. Show expected/actual observations, source identities and the reduced save action. This is what you can hand to a coding assistant. No live code generation is required for the demo.
5. **Verify, rather than trust, the repair (60 seconds).** From the failing report, select the prepared compatible revision. Replay the retained case. Show original data, declaration and actions reused, followed by VERIFIED FOR RETAINED CASE.
6. **Show memory (60 seconds).** Open the regression library. Show the failure and linked repair result. Explain that a future supplied revision can be checked against the same case. If rehearsed time permits, supply the broken revision again: the same case returns NOT FIXED. A previous successful repair never grants future revisions a permanent pass.

The strongest ending is a verified repair followed by detection of the reintroduced bug. Do not claim the library automatically monitors future changes: replay is explicitly invoked today. Retained checks are selected through FalkorDB during the repair replay.

## Make the workflow reliable

### Protect the meaning of a pass

- Keep approval explicit. Never replace an approved expectation just because the changed app produces a different result.
- Reuse the original saved state and reduced actions during repair verification.
- Treat graph/model/browser failures as incomplete or errors, never successful checks.
- Preserve retained-case obligations even if a repair removes the original current dependency.
- Display that a result belongs to a specific case and supplied revision, not the whole app.

### Rehearse positive and negative controls

Run these before recording the submission:

```powershell
cd D:\state-survival-gate
python -m unittest test_library test_record_repair_guards test_prototype test_todomvc -v
python test_record_approve_repair_ui.py
python test_library_ui.py
python preflight.py
python verify_demo.py
```

Docker FalkorDB and the dashboard must be running; local-agent tests also require Ollama and its configured model. Confirm the injected revision fails, the compatible revision passes, an ineffective repair still fails, and removing the current impact path does not skip the retained case. Check approval and source-integrity guards as well as the happy path.

`preflight.py` checks service reachability and model installation. `verify_demo.py` runs the real local model through failure, supplied repair and reintroduced failure on TodoMVC and the separate controlled Corner Shop fixture. It verifies graph-stage snapshots against stored relationships, retained obligations, query results and reuse of data/rules/actions. Receipts are written to `LIVE_DEMO_RECEIPTS.json`. Corner Shop is a second independent controlled example, not another external production application.

For the new features, verify the brief download contains the actual failure and source hashes, omits the raw storage snapshot, and rejects passing runs. Check that the library survives a dashboard restart, opens the right original failure, and links only matching repair attempts. Review exported inputs for private content before sharing.

### Keep the presentation repeatable

- Use the pinned sample and already installed dependencies. Avoid installs and cloud calls on stage.
- Record browser errors and retain receipts, screenshots, source hashes and reports.
- Rehearse the exact click sequence twice. Confirm the same failure and repair outcomes, while allowing timestamps and generated IDs to differ.
- Keep one real saved run as a fallback. Clearly disclose when showing saved evidence.
- If the model is unavailable, explicitly choose deterministic mode and explain that distinction. Do not imply an agent ran.
- Confirm that the graph viewer is showing the current run's graph, not an earlier tab.

## Submission claim

“ParivartanParakh records a developer-approved preservation rule, queries runtime dependencies in FalkorDB, reproduces a shared-data regression, exports a repair handoff, and verifies supplied revisions against the retained original case.”

Not established: arbitrary-app coverage, automatic repair, productivity gains, market demand or uniqueness. A polished controlled demonstration is evidence of the mechanism, not those broader claims.

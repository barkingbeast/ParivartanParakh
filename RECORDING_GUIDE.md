# Record a workflow and verify a repair

Open http://127.0.0.1:8772/ and choose **TodoMVC · injected regression**.

## Record and approve

1. Click **Record a workflow instead**. The local preview starts with a separate browser-storage origin.
2. In the embedded old app, type a task and press Enter. Add a second task; mark the first complete.
3. Click **Select behavior to protect**, then click one task row inside the preview. The recorder groups the repeated list rows and captures their text and checkbox states.
4. Click **Continue to changed feature**. The new build loads at the same preview origin with the old data retained.
5. Click the focus-view feature's preview and save controls.
6. Click **Suggest preservation rule**. Review the captured values, generated actions and observed reader/writer module candidates.
7. Confirm that these values should survive. The confirmation checkbox starts unchecked; the save button remains disabled until it is checked.
8. Name and save the approved workflow, then click **Investigate this approved workflow**.

The recorder generates the manifest; no selectors or storage keys need to be typed for this example. Selecting a supported app folder requires only old/ and new/ static builds, not a prewritten manifest. The source revisions and approved declaration are retained under recorded_workflows/.

Suggestions are deterministic observations, not inferred product requirements. A module candidate reflects storage calls observed during the phase; it is not proof of semantic ownership. Confirm ambiguous candidates. The approved manifest has an integrity digest to detect accidental edits; this is not authentication or an adversarial signature.

## Verify a supplied repair

1. Open the completed failing investigation.
2. Under **Verify a supplied repair**, choose the failed behavior and **TodoMVC · compatible revision**, or supply a local repair build folder.
3. Run the retained-case replay.

The backend reuses the exact failed run localStorage snapshot, original preservation declaration and reduced action sequence. It ignores any replacement manifest supplied alongside the repair. It verifies the old JavaScript source hashes before preparing the replay.

FalkorDB receives a `RegressionCase -[:REQUIRES_REPLAY]-> Feature` obligation. The corresponding query selects the retained check even if the repair has no current shared-key dependency. A successful replay is labelled **VERIFIED FOR RETAINED CASE**, never universal application safety. An ineffective repair is **NOT FIXED**; missing evidence remains **INCOMPLETE**.

## Limits

- Trusted local static app revisions, flat JavaScript module attribution, native localStorage and up to 12 actions per phase.
- Capture supports text input, Enter/Escape/Tab, button/link clicks, and checkbox changes. It does not support drag/drop, arbitrary navigation, radio controls, framework source maps, asynchronous workflow discovery or backend data.
- Observation supports selected text, input values and checkbox states; repeated li/tr/listitem rows can be selected as a group.
- Password inputs are excluded. Preview resources are restricted to the local origin; this is not a sandbox for untrusted application code.
- The expectation must hold in the old app after replay and reload. If it does not, the run is incomplete rather than silently replacing the approved expectation.
- Recording does not automatically approve a rule, infer all user intent, or repair source code.
- Raw storage snapshots and recorded input remain local. Generated recordings, repair workspaces and run artifacts are excluded from Git by default.

## Verification commands

With Docker FalkorDB and the dashboard running:

```powershell
python test_record_approve_repair_ui.py
python -m unittest test_record_repair_guards test_prototype test_todomvc -v
python run_gate.py
```

The UI verification uses a copy with no input manifest and labels its confirmation **automated-test**. It does not claim that the human user approved those synthetic test values.

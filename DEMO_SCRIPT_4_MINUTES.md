# ParivartanParakh: action-by-action recording script

This is the current teleprompter source and replaces the old eight timed sections.

For every card: DO the action, WAIT for the stated screen, then SAY the narration. Read only SAY aloud. Press Next only after all three are complete. Never read the next result before it appears. Pause while processing; shorten waiting periods with labelled cuts if needed. Aim for about four minutes of narration and demonstration, but rehearse the actual click timing first.

Do not refresh Chrome during workflow recording. Keep OBS on Chrome Window Capture so these notes remain outside the recording. If a result differs from the WAIT condition, stop and troubleshoot instead of reading a success claim. Prepared revisions contain a deliberately injected bug; this is not an upstream TodoMVC defect.

### 1. Opening

**DO:** Keep the dashboard visible. Select TodoMVC · injected regression. Keep Use local investigation agent checked. Do not start a run yet.

**WAIT:** The dashboard is ready and OBS is recording.

**SAY:** I built ParivartanParakh because a new feature from an AI coding tool would sometimes break something I built earlier. This checks whether old behavior and saved data survive a change.

### 2. Open the recorder

**DO:** Click Record a workflow instead.

**WAIT:** The white TodoMVC preview appears under 1. Create the old behavior.

**SAY:** TodoMVC is the example task app we're testing. ParivartanParakh is the tool around it.

### 3. Add the first task

**DO:** In the white app, click What needs to be done? Type Prepare hackathon demo and press Enter.

**WAIT:** Prepare hackathon demo appears as a task row.

**SAY:** First, I create a task.

### 4. Add the second task

**DO:** In the same input, type Submit project and press Enter.

**WAIT:** Two task rows are visible.

**SAY:** And a second task.

### 5. Complete the first task

**DO:** Click the circle to the LEFT of Prepare hackathon demo.

**WAIT:** The first task is crossed out. Submit project is still active.

**SAY:** One task is completed and the other is active. Both must survive the change.

### 6. Select what to protect

**DO:** Above the preview, click Select behavior to protect. Then click the TEXT of either task, not its circle.

**WAIT:** The status says Selected 2 observed rows/fields. Continue becomes enabled.

**SAY:** I select the task rows. The tool captures their text and completion states.

### 7. Open the changed build

**DO:** Click Continue to changed feature →.

**WAIT:** The heading says 2. Exercise the changed feature. The task app loads.

**SAY:** Now I switch to the changed build. Its focus-view extension contains a bug I deliberately introduced for this demo. It is not a bug in the original TodoMVC.

### 8. Preview the new feature

**DO:** Inside the WHITE preview, scroll to the controlled-modification panel. Click Preview focus color.

**WAIT:** The preview color changes.

**SAY:** I try the new focus setting.

### 9. Save the new feature

**DO:** In that same panel, click Save focus view.

**WAIT:** The click has completed. Do NOT refresh Chrome.

**SAY:** Then I save it. Next we will check what that save does to the original data.

### 10. Review the proposed rule

**DO:** Above the preview, click Suggest preservation rule →.

**WAIT:** 3. Review and approve appears. Both original tasks are listed: first checked=true, second checked=false.

**SAY:** The suggested rule preserves both original tasks, including which one was completed. I review that expectation.

### 11. Approve the rule

**DO:** Set Workflow name to Demo task preservation. Leave reader/writer selections as generated. Tick I confirm these observed values and checkbox states should survive... Then click Approve and save workflow.

**WAIT:** Workflow approved and saved appears.

**SAY:** I approve the rule. The tool captures evidence, but I decide what should remain true.

### 12. Start the investigation

**DO:** Click Investigate this approved workflow ↗.

**WAIT:** Wait silently until a final report appears. Do not click Run investigation again.

**SAY:** The investigation replays the workflow and reloads the test app automatically.

### 13. Show the failure

**DO:** Find the report heading and the before/after comparison. Point at the completed task missing on the changed side.

**WAIT:** REGRESSION REPRODUCED is visible, with both original tasks on the left and only the active task on the right.

**SAY:** The completed task disappeared. The faulty save overwrote the original list with unfinished tasks. The browser reproduced that failure.

### 14. Explain the dependency

**DO:** Scroll slightly UP to Why these checks? Point at the connected boxes.

**WAIT:** Changed writer → storage key ← reader → feature to check is visible.

**SAY:** The changed focus module writes the task store. The existing task module reads that same store. FalkorDB follows this relationship to identify the older behavior that needs checking.

### 15. Show the agent decision

**DO:** Scroll DOWN to Agent tool trail. Find query_dependencies and expand its Tool result.

**WAIT:** The query result and selected target are visible.

**SAY:** The local AI selects validated tools and checks from graph results. The backend runs reviewed Cypher. Browser assertions determine whether the behavior passed.

### 16. Show FalkorDB

**DO:** Find How the graph changed. Click Open this run in FalkorDB ↗. Switch to the new tab. Click the purple Run button if the graph is blank.

**WAIT:** The current investigation graph shows connected nodes. If the viewer asks for login, pause the recording and connect before continuing.

**SAY:** This is the actual FalkorDB graph for this investigation. The graph selects what needs checking; the browser establishes whether it broke.

### 17. Show the reduced failure

**DO:** Return to the PROJECT tab. Find the before/after comparison. Expand Inspect reproducing actions.

**WAIT:** The reduced action list includes Click #save-focus; the preview-color action was removed.

**SAY:** The reducer removes the unnecessary preview action. Saving alone reproduces this failure.

### 18. Download the repair brief

**DO:** Scroll UP to The old behavior did not survive. In its colored header, click ↓ Repair brief for your coding assistant. Stay in Chrome; do not open the file.

**WAIT:** Chrome shows the Markdown download.

**SAY:** The brief gives a coding assistant the expectation, reproducing actions, and dependency evidence.

### 19. Run the supplied repair

**DO:** Note the ORIGINAL failure run ID at the top of the report. Scroll to Verify a supplied repair. Under Supplied revision choose TodoMVC · compatible revision. Leave the folder field empty. Click Replay retained failure against repair →.

**WAIT:** Wait silently for the new report to finish.

**SAY:** I've prepared a compatible revision. We check it against the original failing case, rather than accepting a new, easier test.

### 20. Show the verified repair

**DO:** Show the repaired before/after comparison. Then scroll to Retained-case repair verification.

**WAIT:** VERIFIED FOR RETAINED CASE and all three reused fields are true. Both tasks survived.

**SAY:** Both tasks survive. The original saved data, preservation rule, and reduced actions were reused. This pass applies to this retained case.

### 21. Show the retained obligation

**DO:** In this REPAIR report, find How the graph changed. Expand Retained failure requires replay. Point at the added REQUIRES_REPLAY relationship.

**WAIT:** The added RegressionCase → REQUIRES_REPLAY → Feature relationship is visible.

**SAY:** The graph retains an obligation to replay the original regression case, even if a later revision changes the dependency.

### 22. Find the original failure

**DO:** Click Library in the left navigation. Paste the ORIGINAL failure run ID into Find an app, behavior or run. In that case click Open failure and verify a supplied revision →.

**WAIT:** You are back on the ORIGINAL failing report, not the passing repair report.

**SAY:** The regression library keeps the original failure and its repair history.

### 23. Try the broken revision again

**DO:** Under Verify a supplied repair, set Supplied revision to TodoMVC · injected regression. Click Replay retained failure against repair →.

**WAIT:** Wait for the report. Scroll to Retained-case repair verification and show NOT FIXED.

**SAY:** When I supply the broken revision again, the same retained case fails again. A previous successful repair does not give later revisions a free pass.

### 24. Closing

**DO:** Keep NOT FIXED visible. Say the closing. Pause 2 seconds, switch to OBS, then click Stop Recording.

**WAIT:** The final result stays visible while you finish speaking.

**SAY:** Today, this supports small static JavaScript apps using localStorage. A pass applies to the workflow tested, not the whole app. I used AI coding assistance to build it. The result is a reproducible failure and a way to verify a supplied repair against the original case.

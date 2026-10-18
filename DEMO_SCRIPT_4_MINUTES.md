# ParivartanParakh demo script

Read the narration only. Aim for a conversational pace, about 135 to 145 words per minute. Allow a few pauses for clicks. The time markers are rehearsal targets, not claims about execution speed. If you shorten a wait in the recording, label the cut. If you use saved reports, say, "These are saved results from a real investigation."

## What to say

### 0:00 to 0:25

I built ParivartanParakh because of something I kept running into with AI coding tools. I'd ask for a new feature, it would work, and something I'd added earlier would stop working.

The question I wanted to answer was simple. After this change, does the old behavior still work with the data already saved?

### 0:25 to 1:00

Here's the example. This task app has two saved tasks. I've completed the first one.

Now I've added a focus view that should show unfinished tasks. But its save button overwrites the original task list with the filtered list. After reloading, the completed task is gone.

I deliberately introduced this bug in an extension to TodoMVC. This isn't a defect I discovered in the original app.

### 1:00 to 1:25

I record the old workflow and select the task rows I want to protect. ParivartanParakh captures their text and completion states.

Then I use the changed feature and review the suggested preservation rule. I have to approve it. The tool captures observations; I decide what should remain true.

### 1:25 to 2:05

When I investigate, the browser records which modules read and write browser storage. ParivartanParakh puts those relationships in FalkorDB.

Here's the path. The changed focus module writes the task store. The existing task module reads that same store. That connects the change to the older behavior we need to check.

The local AI calls a dependency-query tool and chooses checks from the returned targets. The backend executes reviewed Cypher. The AI doesn't invent a passing result.

### 2:05 to 2:35

The browser replays the check with the old saved data. Here are the observations before and after. The completed task disappeared.

The reducer also removes the unnecessary preview action. Saving focus view is enough to reproduce this failure.

I can export this repair brief and give a coding assistant the expectation, the failing actions and the relevant dependency path.

### 2:35 to 3:15

I've prepared a compatible revision. Now I ask ParivartanParakh to check it against the original failure.

It reuses the same saved data, the original preservation rule and the reduced actions. The repair can't supply an easier rule.

Both tasks survive this time.

The graph also stores an obligation to replay this case. Even if a repair removes the original dependency, that doesn't let it skip the check that previously failed.

### 3:15 to 3:40

The regression library keeps the failure and its repair attempts.

Now I supply the broken revision again. The same retained case fails again. Passing once didn't give every later revision a free pass.

### 3:40 to 4:00

Today, this supports small static JavaScript apps using localStorage. It verifies declared workflows, so a pass applies to the case we ran.

I used AI coding assistance and checked the implementation with browser tests and negative controls. The result is a reproducible failure and a way to check whether a supplied repair fixes it.

## What to show

| Time | Screen action |
|---|---|
| 0:00 to 0:25 | Show the dashboard overview. Keep the pointer still while explaining the problem. |
| 0:25 to 1:00 | Choose TodoMVC injected regression and click Record a workflow instead. In the old preview, add Prepare hackathon demo and Submit project, complete the first, then reload the preview to show persistence. Only demonstrate actual deletion after continuing to the changed build. Narration here describes the known fault. |
| 1:00 to 1:25 | Select the task rows using Select behavior to protect. Continue to the changed feature. Click its preview and save controls, generate the rule, review both captured task states, explicitly approve it and save it. These actions can begin in the preceding segment; keep the narration aligned with the visible step. |
| 1:25 to 2:05 | Enable local-agent mode and investigate the approved workflow. Show the dependency path and the agent's query_dependencies tool result. Open this run in FalkorDB, select the current graph if needed and execute the preloaded visualization query. Briefly inspect node id properties if captions show internal numbers. Show the executed Cypher from the report rather than typing a new query during narration. |
| 2:05 to 2:35 | Return to the before/after comparison. Point to the completed task missing from the after-state. Expand Inspect reproducing actions and show the reduced save action. Download the repair brief and briefly show its contents. |
| 2:35 to 3:15 | From this failing report, select TodoMVC compatible revision in Verify a supplied repair. Replay it. Show VERIFIED FOR RETAINED CASE and the three reuse fields. Open the repair run's graph and show REQUIRES_REPLAY. The failure graph and repair graph have different names. |
| 3:15 to 3:40 | Search the regression library using the ORIGINAL failure run ID. Show its linked repair attempt. Open that original failure and select TodoMVC injected regression as the supplied revision. Replay it and show NOT FIXED. |
| 3:40 to 4:00 | Finish on the result or library. Keep the scope statement visible if possible. A source-repository link can appear in the final video frame once published. |

## Before recording

1. Run `python preflight.py` in the project folder.
2. Rehearse the recording clicks once. Keep the prepared compatible revision ready.
3. Keep the dashboard and FalkorDB viewer in separate tabs. Sign into the local viewer beforehand.
4. Close unrelated tabs, silence notifications and use a readable browser zoom.
5. Save the original failure ID. Repair verification and recurrence testing must both refer to it.
6. If execution waits push the video beyond four minutes, trim and label the waiting periods. Do not claim an edited sequence ran without cuts.

## Saved evidence fallback

Use DEMO_RUNS.md for a tested failure, verified repair and recurrence sequence. Introduce them as saved results, not a live investigation. Avoid mixing the saved failure ID with a new recording's repair.

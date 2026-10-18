# ParivartanParakh interface

Audience: developers investigating a change and hackathon judges following evidence. The primary task is to record or run a preservation check, understand a failure, then verify a supplied repair.

Direction: a compact investigation workbench. Put setup and recent activity in a left column; give browser evidence the main workspace. Graph context explains the result and remains directly inspectable. Existing semantics, explicit approval and result boundaries stay intact.

Selected design: **Graphite Inspector**, based on UI UX Pro Max's Data-Dense Dashboard style and Developer Mono typography. Preserve the existing investigation workflow; use a narrow fixed navigation rail on desktop and native anchor navigation on mobile.

Tokens: graphite canvas #111317; surface #1b1e24; foreground #edf0f7; muted #a5afc0; selection/link #9eb8ff; action #4268d2. Teal and rose preserve the existing evidence/status meanings. App screenshots retain original colors as evidence.

Type: locally bundled IBM Plex Sans (400,600) for interface and headings; JetBrains Mono (400) for code, hashes, dependency identities and counters. font-display: swap; local system fallbacks. Licenses are retained in prototype_ui/fonts/.

Search provenance: the first system search matched the dark coding style and developer typography, but returned an unsuitable FAQ landing pattern. One narrower retry matched Data-Dense Dashboard but still suggested a marketing pattern. Neither marketing pattern was adopted or persisted as verified guidance. The selected style/typography matches are applicable; shell layout and blue action colors are deliberate project-specific choices that preserve the user's dark-workbench direction.

Layout:

```text
brand                  Investigate | Evidence | Regression library
Compact title and one-sentence explanation
----------------------+-----------------------------------------
Choose app            | Investigation result / actionable empty
Run or record         | Old state       | Changed state
Advanced controls     | Dependency path / graph stages
Recent runs           | Reproducer / tools / supplied repair
----------------------+-----------------------------------------
Searchable regression library, progressive disclosure and paging
```

Review against brief: avoid a marketing hero, generic metric tiles and ornamental graph animation. The distinctive moment is the real before/after state comparison. Use restraint elsewhere. Stage snapshots are labelled as captured evidence; nothing implies live monitoring or arbitrary Cypher generation.

Quality floor: semantic landmarks, labelled fields, visible keyboard focus, skip link, no hidden approval shortcuts, reduced-motion support, wrapping long hashes/paths, mobile single column and explicit empty/error states. Preserve existing DOM IDs used by execution and browser tests.


## Current palette: user reference

The user's attached dashboard reference takes precedence over earlier palette choices: mint outer canvas #c4d5cb, charcoal frame #222623, coral verdict header #ff6957, icy cyan graph/selection #b6f0fa, mint preserved-state panels. Rounded panels and a compact navigation rail echo the reference. Map color to real content: coral marks verdict attention, cyan highlights dependency evidence, mint frames preserved observations. Keep text/status labels and original screenshots; do not add fabricated charts or business metrics.

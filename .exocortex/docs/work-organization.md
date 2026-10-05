# Know where the work is

A project can have several working folders. They are not separate applications,
and they do not automatically share new saves. Start with `/where`: it reports
this project's linked Git worktrees, branch and commit, template version,
uncommitted work, and distance from the locally known trunk. `/updates` uses the
same collector to show one row per project across explicitly selected roots.
Use `--details` for its working folders. Other computers are not inspected.

Each report names the observed machine and selected scope. Git's worktree
registry includes Claude, Codex and other tools equally, including nested
`.claude/worktrees` folders and registered working folders outside the selected
scan roots. `/updates` expands that registry even when its directory scan stops
at a project root. Branch prefixes and folder names are hints, not evidence of
which assistant created or last used a checkout. Separate clones must fall
within the selected roots or be selected explicitly. Inspect another machine
only when requested, and label its separately observed results with that machine
and observation time. Local paths and machine names never enter portable event
metadata or the public template's saved reports.

Use the repository's declared default branch as trunk. Cached `origin/HEAD` is
preferred; local `main` or `master` is an explicitly labelled fallback. If these
are absent, the trunk is unknown. Cached refs do not prove today's GitHub state.
Favor short-lived task branches and reuse a suitable free worktree. Resume an
existing task deliberately after checking its branch, base and unfinished work.
A task branch is normal; an old checkout is a reason to inspect, not to delete.

Keep these states separate:

- **Saved locally:** a narrative exists in this checkout.
- **Committed locally:** the intended files are in a named Git commit.
- **Pushed:** the required commit and memory were verified on the intended remote.
- **Merged:** the relevant changes were verified on the project's trunk.
- **Deployed:** the intended target's running artifact and health were verified.

The first-phase offline collector cannot certify pushed, process-use, PR or
live-deployment status. It says unknown. Ahead/behind counts describe commit
ancestry, not content equivalence after squash merges or copied changes. Age,
branch names, a clean index, or a merged PR alone never authorize retirement.

Portable project history belongs in the consuming project's Git: notes, lessons,
decisions and events. New events have an event ID and structured branch/commit
scope. A save can describe unfinished work without claiming it is present in
another checkout. Explicitly commit and push the intended memory, then fetch or
pull it on the other computer under the project's normal Git policy. Conflicting
handwritten notes need review; never resolve them by replacing one whole memory
folder. Dirty or unpushed code does not prevent a narrative save.

Keep absolute paths, machine observations, locks, caches, authority and secrets
local. The collector's JSON and expanded tables contain local paths; do not
publish them. It identifies related worktrees by Git's common directory and
separate clones by a sanitized origin host/repository identity. Remote renames,
transfers, aliases, local-path remotes and forks need explicit reconciliation;
there is no universal identity or cross-machine registry in this phase. Forks
with different origins remain separate. No adopter account or identity is
prepopulated. The official template release source is independent of the
consumer's project or account selection.

Generated Session Context is a derived historical view. Its local receipt binds
the view to the checkout, branch and commit. Entry commands only check and report
staleness; an approved save or explicit refresh rebuilds it while preserving
handwritten content. Do not symlink memory folders or copy generated context as
an authoritative replacement. A Git commit or branch switch can invalidate the
view even if the event files have not changed.

Before consolidation, run an explicitly requested `/where --memory` inspection.
It hashes only declared notes and events in this project's linked checkouts,
reports unique content, exact content copies and conflicting filenames, and
leaves every file untouched. Unreadable, linked or over-limit inputs mean
incomplete evidence. Identical bytes in another local folder are not a remote
backup. Ignored files, stashes, other clones and service dependencies still need
separate preservation checks. No cleanup operation is implemented here.

The public template distributes generic code and fictional examples. It never
distributes a maintainer's memory, reports, paths, credentials or task state.
Automatic cleanup, background reports and deployment are later opt-in work;
this phase creates no scheduled jobs and sends no notifications.

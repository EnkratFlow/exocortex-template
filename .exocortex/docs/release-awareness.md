# Release awareness

Release awareness answers “is there a newer Exocortex release?” without
updating anything. It is opt-in per project. It reads only public GitHub stable
release metadata, anonymously; it does not send project names, installed
versions, paths, briefs or memory. It never opens credential files or uses the
GitHub CLI account. Private sources and enterprise hosts are not supported in
this version.

## Start and stop

Use `/updates release enable OWNER/REPO` with the explicitly chosen template
release repository. Enabling writes local consent but makes no network request.
Then use `/updates release check` for the first check. This is separate from
`/updates` repository discovery, which retains its existing account/root scope.
The command specification in `commands/updates.json` is the behavior authority.

| Action | Effect |
|---|---|
| `/updates release status` | Read cached status; no network or writes |
| `/updates release enable OWNER/REPO` | Record this project's chosen public source and opt-in |
| `/updates release check` | Check if due; otherwise use the cache |
| `/updates release remind X.Y.Z` | Hide that release's fresh update notice for 24 hours |
| `/updates release disable` | Stop this project's future checks; preserve the cache |

The corresponding CLI is:

```text
python3 .exocortex/scripts/release_awareness.py status
python3 .exocortex/scripts/release_awareness.py enable --repository example-org/template
python3 .exocortex/scripts/release_awareness.py check
python3 .exocortex/scripts/release_awareness.py remind --version 2.0.0 --hours 24
python3 .exocortex/scripts/release_awareness.py disable
```

Optional `--project-root <root>` and `--cache-dir <directory>` precede the
subcommand. All consuming projects should use the same machine cache to share
the cadence. The source has no personal or consuming-repository default.
Enable, disable, remind and check require applicable owner authorization;
status and help remain read-only. These local records are cooperative consent,
not signed authority or permission to apply an update.

## Entry and notices

`/work` and `/onboard` only run **status**. They do not fetch releases, create
caches or change reminders. After explicit opt-in, a separately authorized host
entry hook can invoke **check** before those commands. The same operation is
available explicitly through `/updates release check` when no hook is installed.
This release installs no hook, timer, scheduler, notification service or daemon.
The existing Cursor phase reminder remains unchanged.

A fresh update notice offers release notes, remind later or planning the update.
The notes link is constructed for the configured source and stable tag, never
copied from an arbitrary response URL. Release prose is not retained or
executed. Remind-later affects only that version and project; a newer release
can notify immediately after its check. Current or disabled states stay quiet.
Stale, unavailable and unknown installed versions never become “up to date.”

Example: “Exocortex 2.0.0 is available; this folder has 1.0.0. Last checked
at the displayed timestamp. Review notes, remind later, or plan the update.”
An offline notice instead identifies the last successful check and labels its
version comparison as last-known evidence. Timestamps are UTC Unix seconds in
JSON; the assistant should display a readable local time.

## Cache and failure behavior

- One cache entry per canonical public source, channel and anonymous scope.
  Two projects using the same source share it. No private account cache is mixed in.
- At most one attempt per 24 hours. Repeated failures back off to two, four,
  then seven days. Numeric server retry delays can extend the wait up to seven
  days. There is no force flag that bypasses the cadence.
- Reserve the next attempt before networking. A crash preserves the previous
  successful metadata and prevents repeated requests from each session.
- A per-source writer lock prevents concurrent checks. Do not delete an active
  lock. After a crash, an operator must verify no writer is active before an
  explicitly authorized recovery; the helper never silently discards state.
- The network subprocess has a 12-second total timeout, 5-second socket timeout
  and 512 KiB response limit. Redirects are not followed. Errors are sanitized;
  “network attempted” does not claim a successful connection.
- A failed attempt retains the last successful release, timestamp and safe
  error code. Overdue or failed evidence is stale. A backwards clock or corrupt
  state requires reconciliation and does not trigger automatic repair.

Project opt-in/reminders live in `.exocortex/local/release-awareness/config.json`.
The default machine cache is `exocortex/releases` under macOS `Library/Caches`,
Windows `LOCALAPPDATA`, or Linux `XDG_CACHE_HOME` (falling back to `.cache`).
Local configuration, caches and locks never enter portable memory or the public
package. Choosing a separate cache directory creates a separate cadence scope;
keep the same override across projects, and do not share machine caches via Git.

## Boundaries and evidence

This is version awareness, not release-artifact authentication or readiness to
install. Selected-project updates remain a later phase using the existing safe
updater's approval, preservation, verification and recovery process. A newer
release does not authorize downloads, installs, Git operations or deployment.

The public transport follows the documented
[GitHub latest-release API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release).
Only stable numeric `X.Y.Z` tags with an optional `v` prefix are compared, using
the same version functions as the inventory and the shared local-version reader.
Focused tests use fictional responses and disposable caches; they do not certify
a live provider, proxy configuration, native host hook or Windows environment.

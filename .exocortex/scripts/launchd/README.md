# Legacy Auto-Snapshot Adapter

Automatic snapshots are retired in public-v2. `auto_snapshot.sh` is
reminder-only and performs no repository scan, event write, checkpoint,
credential read, provider call, or external sync.

The install and uninstall scripts fail closed because global launchd changes
are outside project-local repository authority. Existing system agents, if
present from an older installation, must be audited and removed through a
separately approved system-operation work item. Repository installation and
update never load, unload, copy, or delete global launchd state.

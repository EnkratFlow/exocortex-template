# External Memory and RAG Integration

External memory is disabled by default. No command reads credential files,
discovers endpoints, calls MCP, copies to a vault, or sends project content
automatically.

To authorize one outward payload:

1. Approve and issue a one-time `inspect_egress_payload` local capability for
   the exact project-relative source path and registered executor.
2. Run `egress_guard.py inspect`. It consumes that capability before opening
   the source and returns metadata only: digest, size, class, object path, and
   descriptor path. It creates no descriptor or payload object.
3. Approve and issue a separate one-time `prepare_egress_payload` capability for those
   exact values and registered executor.
4. Run `stage`; it creates immutable content-addressed local state only.
5. Review the descriptor without reading credentials.
6. Separately approve the exact destination ID, method, descriptor, digest,
   outward effect, and expiry under the deny-by-default project policy.
7. Run `send`. Metadata is checked before payload access; bytes are verified;
   credentials are resolved only afterward; authority is rechecked and consumed
   immediately before transport, with one final policy recheck after credential
   lookup.

No indeterminate send is automatically retried. A new approval is required
unless the destination has an explicitly tested idempotency contract bound in
policy and capability.

Legacy `sync_event_to_vault.sh` and `post_to_hub.sh` accept only
`inspect|stage|send` egress-guard arguments. Passing an event path directly is
denied before credential or payload access.

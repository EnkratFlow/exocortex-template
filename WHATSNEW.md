What's new in 3.1.1
─────────────────────

✦ Plan-orchestrate rule now has a Model pins table at the top.
  Bump a model (new haiku, new sonnet) in one place and every
  reference in the rule picks it up. Eliminates search-and-replace
  on future model upgrades.

✦ Step 5b /save prompt template tightened. The CRITICAL FORMATTING
  RULES block now spells out every forbidden metadata field by
  name, so the haiku save subagent never produces duplicate
  `<!-- Event Metadata -->` headers.

For everything else, see 3.1.0:
  https://github.com/EnkratFlow/exocortex-template/blob/main/CHANGELOG.md

(3.1.0 shipped plan orchestration, the auto-save phase hook, and
the batch updater. 3.1.1 is a docs-only patch on top.)

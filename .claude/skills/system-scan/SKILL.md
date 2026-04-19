---
name: system-scan
description: Read repository and produce system health report
disable-model-invocation: true
---

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol and step execution rules.

**Then execute this command:** Run the steps in `.exocortex/commands/system-scan.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.

1) Read Repository:
   You must read:
   - Application code
   - Architecture and design documents
   - Requirements and specifications
   - QA and testing documentation
   - Project memory and control files

2) Produce Report:
   Single markdown report that answers:
   1. What this system is and what problem it solves
   2. What is implemented and considered complete
   3. What is currently in progress
   4. What is explicitly planned next (based only on existing docs and memory)
   5. Where that next work belongs (which repo / folder)
   6. Any documented risks, gaps, or open decisions

3) Constraints:
   - Do not modify files
   - Do not update memory or TODO
   - Do not invent work or roadmap items
   - Do not speculate beyond documented evidence

4) Output:
   - One markdown document
   - Written for a senior engineer new to the system
   - Clear, factual, and actionable

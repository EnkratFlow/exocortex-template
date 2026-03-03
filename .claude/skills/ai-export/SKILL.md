---
name: ai-export
description: Export system understanding for another AI
disable-model-invocation: true
---

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol and step execution rules.

**Then execute this command:** Run the steps in `.exocortex/commands/ai-export.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.

1) Scope:
   Read:
   - Application code
   - Architecture documentation
   - Requirements and specifications
   - QA and testing documentation
   - Project memory (.exocortex/MEMORY.md and referenced files)

2) Tasks:
   1. Explain what the system is and what problem it solves
   2. Describe the high-level architecture and major components
   3. Identify core responsibilities and boundaries
   4. Summarize how data flows through the system
   5. Describe QA strategy and validation approach (automated + human)
   6. Note explicit constraints, invariants, and governance rules from memory
   7. Call out known risks, gaps, or intentional omissions if documented

3) Rules:
   - Do not change any files
   - Do not update memory or TODO
   - Do not propose refactors
   - Do not speculate beyond documented evidence
   - If confidence is low, say so explicitly

4) Output:
   - Produce a single markdown document
   - Use clear section headings
   - Write for an external AI unfamiliar with the project
   - Keep it factual and concise

   This output will be copied into another AI for analysis.

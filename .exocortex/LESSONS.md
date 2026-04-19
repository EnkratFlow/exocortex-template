# Project Lessons – [PROJECT_NAME]

**Last Updated:** [DATE]  
**Purpose:** Prevent repeating mistakes in this codebase

---

## How to Use This File

1. **Before major changes:** Scan relevant lessons
2. **After painful debugging:** Add new lesson
3. **When stuck:** Check if similar problem happened before

For cross-project lessons (Python, Docker, cost optimization), see:  
`[PARENT_PROJECT]/docs/WORKFLOWS/LESSONS_LEARNED.md`

---

## Template: How to Add a Lesson

When you learn something the hard way, document it here to prevent repeating the mistake:

### LESSON [NUMBER]: [Short Title] ([Date])

**What Went Wrong:**
[Describe what didn't work or what mistake was made]

**Why It Happened:**
[Explain the root cause - what led to this mistake?]

**What Worked:**
[Describe the solution or correct approach]
```
[Optional: Code example showing the correct pattern]
```

**Prevention:**
[How to avoid this problem in the future - specific guidelines or checks]

---

## Example Lesson (Delete This After Adding Real Lessons)

### LESSON 1: Always Validate Input Early (Example Date)

**What Went Wrong:**
- Application crashed when user submitted form with empty required field
- Error occurred deep in the processing logic, not at the entry point
- Difficult to debug because stack trace was far from the actual problem

**Why It Happened:**
- No input validation at API endpoint
- Assumed frontend validation was sufficient
- Backend processing logic expected valid data

**What Worked:**
```javascript
// ✅ CORRECT: Validate at entry point
app.post('/api/submit', (req, res) => {
  const { username, email } = req.body;
  
  if (!username || !email) {
    return res.status(400).json({ error: 'Missing required fields' });
  }
  
  // Now safe to process
  processSubmission(username, email);
});
```

**Prevention:**
- Always validate input at API endpoints
- Never trust client-side validation alone
- Use validation middleware for consistent checks
- Add integration tests for invalid input cases

---

## [Month Year] Lessons

[TODO: Your lessons will go here as you discover patterns and anti-patterns]

---

## Red Flags (Stop and Think)

[TODO: Add project-specific warning signs that indicate you should pause and reconsider]

| Red Flag | Response |
|----------|----------|
| Example: File is 1000+ lines | Consider splitting into modules |
| Example: Third identical copy of code | Extract to shared function |
| Example: Same bug appearing twice | Add lesson and prevention strategy |

---

## Project-Specific Patterns

[TODO: Document recurring patterns specific to your project]

**Good Patterns (Keep Using):**
- [Pattern that works well in your codebase]

**Anti-Patterns (Avoid):**
- [Pattern that causes problems in your codebase]

---

**Remember:** The goal is to learn from mistakes and share that knowledge. Don't be afraid to document painful lessons - they're the most valuable ones!

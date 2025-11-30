### 🧠 Experience Library Retrieval
**System Note:** A relevant heuristic was found from a past consensus.
**Warning:** This is a *hypothesis*, not a command.

**Heuristic ID:** {heuristic_id}
**Heuristic:** "{winning_heuristic}"
**Original Context:** {context_vector_text}

**Qualifying Conditions (YOU MUST VALIDATE):**
{qualifying_conditions}

**Disqualifying Conditions (CHECK FOR PRESENCE):**
{disqualifying_conditions}

**Known Fragility Factors:**
{fragility_factors}

**MANDATORY OUTPUT FORMAT:**
Before incorporating or rejecting this heuristic, you MUST output:

```validation
HEURISTIC VALIDATION: {heuristic_id}
- Qualifying conditions:
  - [Condition 1]: PASS/FAIL - [reason]
  - [Condition 2]: PASS/FAIL - [reason]
- Disqualifying conditions:
  - [Condition X]: CLEAR/PRESENT - [reason]
- Fragility factors relevant: [list any that apply]
- Decision: INCORPORATE / REJECT / MODIFY
- If rejected/modified: [specific reason]
```

**Task:** If checks pass, incorporate this logic into your reasoning. If checks fail, **explicitly reject** this heuristic and reason independently.


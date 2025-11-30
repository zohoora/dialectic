### 🧠 Experience Library Retrieval (Multiple Heuristics)

**⚠️ COLLISION DETECTED** between Heuristic A and Heuristic B
**Collision Type:** {collision_type}
**Resolution Hint:** {resolution_hint}

---

**Heuristic A** (ID: {h1_id})
**Confidence:** {h1_confidence} | **Validations:** {h1_times_accepted}
**Heuristic:** "{h1_winning_heuristic}"
**Qualifying:** {h1_qualifying_conditions}
**Disqualifying:** {h1_disqualifying_conditions}

---

**Heuristic B** (ID: {h2_id})
**Confidence:** {h2_confidence} | **Validations:** {h2_times_accepted}
**Heuristic:** "{h2_winning_heuristic}"
**Qualifying:** {h2_qualifying_conditions}
**Disqualifying:** {h2_disqualifying_conditions}

---

**MANDATORY OUTPUT FORMAT:**
You must validate EACH heuristic independently:

```validation
[HEURISTIC A VALIDATION]
- Qualifying: [PASS/FAIL for each]
- Disqualifying: [CLEAR/PRESENT for each]
- Decision: INCORPORATE / REJECT

[HEURISTIC B VALIDATION]
- Qualifying: [PASS/FAIL for each]
- Disqualifying: [CLEAR/PRESENT for each]
- Decision: INCORPORATE / REJECT

[COLLISION RESOLUTION]
If both pass: Which applies to this patient and why?
```

**Task:** These heuristics may conflict. If both validate, explicitly argue which applies. If the conflict cannot be resolved, flag as "Genuine Clinical Equipoise."


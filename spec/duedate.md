# DueDate — EARS requirements (spec-driven; written before code)

EARS = Easy Approach to Requirements Syntax. "The system shall / When <trigger>, the
system shall ..." Each requirement is testable.

## Ingestion
R1. When a user submits a notice image or PDF, the system shall extract text with Amazon
    Textract and retain each line's text, geometry, and confidence as the citation substrate.
R2. The system shall accept JPG, PNG, and single/multi-page PDF up to 10 MB.
R3. The system shall not require an account or login to analyze a notice.

## Deterministic fact extraction (NO LLM)
R4. The system shall classify the notice into one of: pay-or-quit, cure-or-quit,
    unconditional-quit, termination-30/60/90, or unknown — using rule-based matching over
    extracted text, and shall cite the line(s) that triggered the classification.
R5. The system shall extract, by rule, any explicit deadline date, dollar amount owed,
    named parties, and property address, each with the citing line id, or mark them absent.
R6. When the notice states a number of days rather than a date, the system shall compute
    the deadline date from the stated issue/service date using a documented rule and shall
    label the computed value as computed, showing the rule used.
R7. The system shall never output a date or amount that is not either present in the
    extracted text or computed by R6 from extracted values.

## Narration + translation (LLM under guardrails)
R8. The system shall use Amazon Bedrock only to translate and simplify the deterministic
    findings into the requested language and reading level.
R9. The system shall constrain the model to the extracted facts and require each sentence
    to reference a fact id; sentences without a backing fact id shall be dropped.
R10. When the notice does not contain information the user asks about, the system shall
    state that the notice does not say it and shall not supply an answer from general
    knowledge.

## Output
R11. The system shall present: the one key deadline (prominent), a dated action checklist,
    the notice type in plain language, the user's stated rights (cited), and a "what your
    notice does NOT say" section.
R12. The system shall link every claim to the exact extracted line it came from, viewable
    on demand.
R13. The system shall route the user to real free legal-aid resources appropriate to the
    detected jurisdiction, and shall state that DueDate is not legal advice.
R14. The system shall offer the output in at least English and Spanish.

## Non-functional
R15. The system shall be served over HTTPS from a public URL with no login wall and a
    one-click sample notice.
R16. The system shall delete uploaded documents within 24 hours (S3 lifecycle TTL).
R17. The UI shall meet WCAG 2.1 AA (contrast, labels, keyboard, language attributes).
R18. Infrastructure shall be defined as code (AWS CDK) and run cost ~ $0 at idle.
R19. A test suite shall prove R7 and R10 (no invented facts; refuses when unsupported).

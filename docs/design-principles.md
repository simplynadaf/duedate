# DueDate - product steering

## What we are building
DueDate reads an eviction notice a tenant received and returns, in plain language and in
the tenant's own language: the single deadline they must not miss, the exact action
required before it, and their stated rights, with every statement pinned to the exact
line of their own notice. It never invents anything the notice does not say.

## Who it is for
Tenants facing eviction who self-represent, often have a disability, speak a primary
language other than English, and have limited access to technology. (MLRI Default Project.)
~1 in 4 eviction cases are lost by default because the tenant never responds in time.

## Non-negotiable principles (enforce in code + UI)
1. Facts are deterministic, never model-generated. Dates, amounts, notice type, parties,
   and the computed deadline come from Textract output + rules. The model cannot alter a fact.
2. Every surfaced claim cites a specific extracted line (block id + text + confidence).
   No citation => do not show it.
3. Refuse to invent. If the notice does not state it, say so and route to free help.
4. Not legal advice. Explain + cite + route to free legal aid. Never recommend a strategy.
5. Private by default. No login. Uploaded notice deleted on a short TTL. Public URL
   reachable by judges and the AI scorer with a one-click sample.

## Tone
Calm, concrete, respectful. Short sentences. Reading level ~grade 6. No legalese unless
quoting the notice (then translate it).

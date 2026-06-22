# Prose Quality Rules — Solo-Code Harness

> Adapted from "The Elements of Agent Style" (Zhao, 2026). Reduces AI-tell patterns in technical prose.

| # | Rule | Severity |
|---|------|----------|
| 1 | **Cut needless words** — "in order to" → "to", "due to the fact that" → "because", "at this point in time" → "now" | high |
| 2 | **Drop dying metaphors** — never "pushes the boundaries", "paradigm shift", "state of the art", "cutting edge" | high |
| 3 | **Use concrete terms** — "performance issues" → "p95 latency rose from 120ms to 450ms" | high |
| 4 | **Prefer plain English** — "use" over "leverage", "method" over "methodology", "because" over "due to the fact that" | medium |
| 5 | **No transition-word openers** — avoid "Additionally", "Furthermore", "Moreover" at sentence start | medium |
| 6 | **Varied sentence starts** — never open two consecutive sentences with the same word | medium |
| 7 | **Support claims with evidence** — never "prior work shows" without naming the source. Never fabricate citations | critical |
| 8 | **Split long sentences** — split sentences over 30 words. Vary sentence length across paragraphs | high |

## BAD → GOOD

- BAD: `This PR makes minor adjustments to fix an issue causing test failures.`
- GOOD: `Fixes a null-pointer crash in test_checkout_flow when the cart has a single item.`

- BAD: `We leverage state-of-the-art embedding models to unlock the retrieval pipeline's potential.`
- GOOD: `We use text-embedding-3-large, raising recall@10 by 7 points over ada-002.`

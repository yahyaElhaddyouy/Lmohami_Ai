# Darija Comprehension Evaluation Report

## Summary

- Total cases: 330
- Passed: 326
- Failed: 4
- Pass rate: 98.8%
- Target: 90.0%
- Status: PASS
- Average latency: 1301 ms
- Median latency: 3 ms
- Max latency: 29333 ms

## Cases By Category

- arabizi: 37
- daily_darija: 50
- emotions: 40
- general_conversation: 20
- general_labor_boundary: 8
- greetings: 15
- labor_boundary: 10
- labor_law: 35
- meaning_questions: 40
- mixed_french_darija: 35
- non_labor_law_legal: 25
- thanks: 15

## Cases By Expected Type

- general_conversation: 230
- greeting: 15
- labor_law: 45
- non_labor_law_legal: 25
- thanks: 15

## Failures By Category

- general_conversation: 2
- mixed_french_darija: 2

## Failed Examples

- mixed_french_darija_005 [mixed_french_darija]: ana stressé mais labas -> classifier expected general_conversation, got greeting
- mixed_french_darija_020 [mixed_french_darija]: merci بزاف على الشرح -> classifier expected general_conversation, got thanks
- general_conversation_005 [general_conversation]: salam wach katfhem darija? -> classifier expected general_conversation, got greeting
- general_conversation_016 [general_conversation]: كيفاش نقول شكرا بطريقة مغربية -> classifier expected general_conversation, got thanks

## Output Files

- `darija_comprehension_results.jsonl`
- `darija_comprehension_failures.jsonl`
- `darija_comprehension_report.md`

## Note

This evaluates the current live chatbot path and routing. It does not prove a QLoRA adapter, because training has not started.

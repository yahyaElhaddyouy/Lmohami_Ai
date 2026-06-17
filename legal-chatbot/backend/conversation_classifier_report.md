# Conversation Classifier Evaluation Report

## Summary

- Total cases: 238
- Passed: 236
- Failed: 2
- Accuracy: 99.2%
- Target: 95.0%
- Status: PASS

## Cases By Expected Type

- general_conversation: 118
- greeting: 15
- labor_law: 50
- non_labor_law_legal: 30
- thanks: 15
- unknown: 10

## Cases By Coverage

- arabizi: 18
- daily_life: 20
- emotions: 20
- explanations: 20
- greeting: 15
- labor_law: 50
- mixed_french_darija: 20
- non_labor_law_legal: 30
- smalltalk: 20
- thanks: 15
- unknown: 10

## Failures By Expected Type

- general_conversation: 2

## Failed Examples

- mixed_french_darija_005 [mixed_french_darija]: expected=general_conversation actual=greeting confidence=0.95 question=ana stressé mais labas
- mixed_french_darija_020 [mixed_french_darija]: expected=general_conversation actual=thanks confidence=0.95 question=merci بزاف على الشرح

## Output Files

- `conversation_classifier_results.jsonl`
- `conversation_classifier_failures.jsonl`
- `conversation_classifier_report.md`

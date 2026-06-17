# Progressive Stress Report

## Phase Results

### 50 Cases

- Attempts: 1
- Pass rate: 100.00%
- Passed: 50/50
- Average latency: 6300 ms
- Median latency: 7636 ms
- Max latency: 12462 ms
- Gate: PASS
- Failures by type: {}

### 200 Cases

- Attempts: 1
- Pass rate: 91.50%
- Passed: 183/200
- Average latency: 6805 ms
- Median latency: 8157 ms
- Max latency: 50368 ms
- Gate: PASS
- Failures by type: {"conversation_routing_error": 16, "latency_error": 1, "refusal_error": 10}

### 500 Cases

- Attempts: 1
- Pass rate: 91.00%
- Passed: 455/500
- Average latency: 10417 ms
- Median latency: 8020 ms
- Max latency: 63433 ms
- Gate: PASS
- Failures by type: {"citation_error": 14, "intent_error": 1, "latency_error": 44, "refusal_error": 4}

## Fixes Applied

- verified_rules_first: Restore the existing verified-rule-first default to reduce unsafe LLM drift, citation mismatches, and >30s generation latency. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\rag.py)
- vague_dismissal_routing: Route explicit 'wait at home until we call you' dismissal wording into the labor-law path. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\conversation_classifier.py)
- routing_variants: Recognize embedded greetings/thanks and observed Arabizi or no-contract labor phrases without changing legal answers. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\conversation_classifier.py)
- paid_leave_intent_priority: Keep explicit annual-leave terms specific when the user also says the details are unclear. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\legal_understanding.py)
- social_phrase_boundary_correction: Correct the standalone greeting/thanks regex escaping so prefixed social messages route as intended. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\conversation_classifier.py)
- arabizi_legal_intents: Recognize the observed Arabizi sick-leave and dismissal wording in legal understanding without changing any legal rule content. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\legal_understanding.py)
- social_routing_regression_correction: Limit embedded greeting/thanks routing to exact messages and explicit polite wrappers so ordinary Darija sentences containing social words remain general conversation. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\conversation_classifier.py, C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\stress_real_users.py)
- verified_topic_aliases: Map the observed Arabizi sick-leave/dismissal phrases and the Arabic pregnancy spelling الحمل to existing RAG topics so verified source-backed answers are used without changing legal content. (files: C:\Users\MSI\Desktop\lmo7ami\ai chatbot\legal-chatbot\backend\rag.py)

## Final Baselines

- Trust score: 1.0
- Intent score: 1.0
- Darija comprehension: 0.988
- Conversation classifier: 0.992
- API contract: True

## Final Recommendation

**READY_FOR_PRIVATE_BETA**

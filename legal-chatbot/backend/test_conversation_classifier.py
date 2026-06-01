# -*- coding: utf-8 -*-

import unittest

from conversation_classifier import classify_conversation


GENERAL_ROUTE_TYPES = {"general_conversation", "greeting", "thanks"}


def route_bucket(question: str) -> str:
    result = classify_conversation(question)
    if result["type"] in GENERAL_ROUTE_TYPES:
        return "general_conversation"
    return result["type"]


class ConversationClassifierTests(unittest.TestCase):
    def test_requested_route_examples(self):
        cases = [
            ("السلام عليكم", "general_conversation"),
            ("شكرا", "general_conversation"),
            ("الجو سخون بزاف", "general_conversation"),
            ("ana m9ele9 bzaf", "general_conversation"),
            ("شنو كتعني دابا نجي عندك", "general_conversation"),
            ("واش كتعرف كازا", "general_conversation"),
            ("قالو ليا ما تبقاش تجي", "labor_law"),
            ("ما خلصنيش المشغل", "labor_law"),
        ]

        for question, expected in cases:
            with self.subTest(question=question):
                self.assertEqual(route_bucket(question), expected)

    def test_specific_greeting_and_thanks_types(self):
        self.assertEqual(classify_conversation("السلام عليكم")["type"], "greeting")
        self.assertEqual(classify_conversation("شكرا")["type"], "thanks")

    def test_non_labor_law_legal(self):
        self.assertEqual(classify_conversation("بغيت نسول على الطلاق")["type"], "non_labor_law_legal")
        self.assertEqual(classify_conversation("عندي مشكل مع مول الدار فالكراء")["type"], "non_labor_law_legal")

    def test_unknown(self):
        self.assertEqual(classify_conversation("؟؟؟")["type"], "unknown")


if __name__ == "__main__":
    unittest.main()

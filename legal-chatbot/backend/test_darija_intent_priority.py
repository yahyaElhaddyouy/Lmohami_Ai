import unittest

from darija_intent import detect_darija_intent


class DarijaIntentPriorityTests(unittest.TestCase):
    def test_maternity_protection_beats_generic_dismissal(self):
        cases = [
            "واش الحامل عندها حماية من الطرد؟",
            "طردوني وأنا حامل",
            "المشغل رفض يرجعني بعد الولادة",
        ]

        for question in cases:
            with self.subTest(question=question):
                self.assertEqual(
                    detect_darija_intent(question).intent,
                    "maternity_protection",
                )


if __name__ == "__main__":
    unittest.main()

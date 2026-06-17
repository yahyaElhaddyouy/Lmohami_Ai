import unittest

from legal_understanding import analyze_question


class LegalUnderstandingTests(unittest.TestCase):
    def test_vague_dismissal_extracts_unclear_dismissal(self):
        analysis = analyze_question("قالو ليا ما تبقاش تجي")

        self.assertEqual(analysis["intent"], "dismissal_unclear")
        self.assertEqual(analysis["facts"]["employer_action"], "told_not_to_return")
        self.assertIn("dismissal_or_suspension", analysis["legal_issues"])
        self.assertTrue(analysis["needs_clarification"])
        self.assertIn("motif écrit", analysis["search_query"])

    def test_pregnancy_dismissal_has_maternity_priority(self):
        analysis = analyze_question("طردوني وأنا حامل")

        self.assertEqual(analysis["intent"], "maternity_protection")
        self.assertEqual(
            analysis["facts"]["employer_action"],
            "dismissal_or_threat_during_pregnancy",
        )
        self.assertIn("maternity_protection", analysis["legal_issues"])

    def test_cnss_deduction_without_declaration(self):
        analysis = analyze_question("كيشدو ليا CNSS ولكن ما مصرحينش بيا")

        self.assertEqual(analysis["intent"], "cnss_non_declaration")
        self.assertEqual(analysis["facts"]["cnss_status"], "deducted_but_not_declared")
        self.assertIn("CNSS déclaration", analysis["search_query"])

    def test_work_accident_inside_work(self):
        analysis = analyze_question("أنا وقع ليا حادث داخل الخدمة")

        self.assertEqual(analysis["intent"], "work_accident")
        self.assertEqual(analysis["facts"]["accident_context"], "inside_work")
        self.assertIn("accident_de_travail", analysis["legal_issues"])

    def test_unpaid_salary(self):
        analysis = analyze_question("ما خلصنيش الباطرون")

        self.assertEqual(analysis["intent"], "salary_unpaid")
        self.assertEqual(analysis["facts"]["salary_status"], "unpaid")
        self.assertIn("salary_payment", analysis["legal_issues"])

    def test_stress_intent_regressions(self):
        cases = [
            ("bghit nsta9el o ma 3arefch lmassatra", "resignation"),
            ("t7t f lkhdma o tjre7t", "work_accident"),
            ("khdemt jouj chhor o ma 3tawni walo", "salary_unpaid"),
            ("charika katmatel f chahadat l3amal", "work_certificate"),
            ("chef gal ma tjich ghda o ma fhemtch", "dismissal_unclear"),
            ("trdoni mn lkhdma bla sabab mektoub", "dismissal"),
            ("الساعات الإضافية ما بايناش فالبولتان", "overtime"),
            ("ana 7amla o patron bgha ytrdni", "maternity_protection"),
            ("3ndi ghir messages m3a patron bach nthbet lkhdma", "contract"),
            ("khsmo lia nhar o ana kont 7ader", "salary_unpaid"),
            ("kifach ndir chikaya 3nd mofatich choghl", "labor_inspection"),
        ]

        for question, expected in cases:
            with self.subTest(question=question):
                self.assertEqual(analyze_question(question)["intent"], expected)

    def test_refused_access_without_maternity_is_unclear_dismissal(self):
        cases = [
            "مخلاونيش ندخل للشركة",
            "منعوني ندخل نخدم",
            "ما قبلونيش نرجع للخدمة",
        ]

        for question in cases:
            with self.subTest(question=question):
                analysis = analyze_question(question)

                self.assertEqual(analysis["intent"], "dismissal_unclear")
                self.assertEqual(
                    analysis["facts"]["employer_action"],
                    "blocked_from_workplace",
                )
                for issue in (
                    "refused_access_to_workplace",
                    "possible_dismissal_or_suspension",
                    "written_reason",
                    "dismissal_procedure",
                ):
                    self.assertIn(issue, analysis["legal_issues"])

    def test_refused_access_after_maternity_keeps_maternity_priority(self):
        cases = [
            "مشيت نولد ومني رجعت الخدمة مخلاونيش ندخل",
            "رجعت من الولادة وما قبلونيش نرجع",
        ]

        for question in cases:
            with self.subTest(question=question):
                analysis = analyze_question(question)

                self.assertEqual(analysis["intent"], "maternity_protection")
                self.assertEqual(
                    analysis["facts"]["employer_action"],
                    "refused_access_after_maternity",
                )
                for issue in (
                    "maternity_leave",
                    "return_to_work",
                    "refused_access_after_maternity",
                    "possible_dismissal_after_maternity",
                ):
                    self.assertIn(issue, analysis["legal_issues"])


if __name__ == "__main__":
    unittest.main()

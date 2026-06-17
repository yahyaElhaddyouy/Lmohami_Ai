# -*- coding: utf-8 -*-
import unittest

from rag import (
    SourceChunk,
    answer_citations_match_sources,
    fallback_answer_from_sources,
    validate_answer_citations,
)


def chunk(number: int, page: str, text: str = "source text", category: str = "code_travail"):
    return SourceChunk(
        number=number,
        page=page,
        text=text,
        category=category,
        source="test.pdf",
    )


class CitationSafetyTests(unittest.TestCase):
    def assert_sanitized(self, answer: str, sources: list[SourceChunk], missing: str):
        sanitized = validate_answer_citations(answer, sources)
        self.assertNotIn(missing, sanitized)
        self.assertTrue(answer_citations_match_sources(sanitized, sources))
        return sanitized

    def test_salary_unpaid_invalid_page_is_replaced(self):
        sources = [
            chunk(1, "125", "article 361 salaire"),
            chunk(2, "126", "article 363 défaut de paiement du salaire"),
        ]
        sanitized = self.assert_sanitized(
            "الأجر خاصو يبقى مرتبط بالمصدر. [المصدر 1، الصفحة 365]",
            sources,
            "365",
        )
        self.assertIn("[المصدر 1، الصفحة 125]", sanitized)

    def test_salary_deduction_swapped_source_number_is_fixed(self):
        sources = [
            chunk(1, "125", "retenue salaire"),
            chunk(2, "126", "paiement du salaire"),
        ]
        sanitized = validate_answer_citations(
            "الاقتطاع خاصو يتراجع مع الوثائق. [المصدر 1، الصفحة 126]",
            sources,
        )
        self.assertIn("[المصدر 2، الصفحة 126]", sanitized)
        self.assertTrue(answer_citations_match_sources(sanitized, sources))

    def test_no_written_contract_invalid_page_is_replaced(self):
        sources = [chunk(1, "19", "preuve de l'existence du contrat de travail")]
        sanitized = self.assert_sanitized(
            "إثبات علاقة الشغل ممكن بالوثائق. [المصدر 1، الصفحة 34]",
            sources,
            "34",
        )
        self.assertIn("[المصدر 1، الصفحة 19]", sanitized)

    def test_work_accident_invalid_page_is_replaced(self):
        sources = [
            chunk(1, "13", "accident du travail", "work_accident"),
            chunk(2, "10", "risques professionnels", "work_accident"),
        ]
        sanitized = self.assert_sanitized(
            "حادث الشغل خاصو توثيق. [المصدر 1، الصفحة 32]",
            sources,
            "32",
        )
        self.assertIn("[المصدر 1، الصفحة 13]", sanitized)

    def test_pregnancy_swapped_source_number_is_fixed(self):
        sources = [
            chunk(1, "64", "congé de maternité"),
            chunk(2, "66", "protection de la maternité"),
        ]
        sanitized = validate_answer_citations(
            "الحماية كتتراجع حسب الوثائق. [المصدر 1، الصفحة 66]",
            sources,
        )
        self.assertIn("[المصدر 2، الصفحة 66]", sanitized)
        self.assertTrue(answer_citations_match_sources(sanitized, sources))

    def test_resignation_invalid_page_is_replaced(self):
        sources = [chunk(1, "31", "article 51 préavis")]
        sanitized = self.assert_sanitized(
            "الاستقالة خاصها تكون واضحة ومكتوبة. [المصدر 1، الصفحة 34]",
            sources,
            "34",
        )
        self.assertIn("[المصدر 1، الصفحة 31]", sanitized)

    def test_latency_fallback_returns_source_backed_answer(self):
        sources = [
            chunk(1, "125", "article 361 salaire"),
            chunk(2, "126", "article 363 défaut de paiement du salaire"),
        ]
        answer, fallback_sources = fallback_answer_from_sources(
            "khdemt jouj chhor o ma 3tawni walo salaire défaut de paiement du salaire",
            sources,
            "khdemt jouj chhor o ma 3tawni walo",
            "high",
            "",
        )
        self.assertTrue(answer)
        self.assertEqual(fallback_sources, sources)
        self.assertTrue(answer_citations_match_sources(answer, fallback_sources))


if __name__ == "__main__":
    unittest.main()

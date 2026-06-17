"""Fact and issue extraction before legal RAG retrieval."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from darija_intent import detect_darija_intent, normalize_text


DEFAULT_FACTS = {
    "worker_status": "unknown",
    "employer_action": "unknown",
    "written_document": "unknown",
    "salary_status": "unknown",
    "cnss_status": "unknown",
    "accident_context": "unknown",
    "pregnancy_status": "unknown",
    "contract_type": "unknown",
}


SEARCH_QUERIES = {
    "dismissal_unclear": (
        "licenciement procédure de licenciement motif écrit audition salarié "
        "Code du travail Maroc"
    ),
    "dismissal": (
        "licenciement motif valable procédure audition procès-verbal "
        "indemnité Code du travail Maroc"
    ),
    "disciplinary_dismissal": (
        "faute grave procédure disciplinaire audition procès-verbal "
        "licenciement salarié Maroc"
    ),
    "maternity_protection": (
        "protection maternité grossesse licenciement certificat médical "
        "congé maternité Code du travail Maroc"
    ),
    "salary_unpaid": (
        "paiement du salaire retard salaire retenue salaire employeur "
        "Code du travail Maroc"
    ),
    "cnss_non_declaration": (
        "CNSS déclaration salarié cotisations employeur Maroc"
    ),
    "work_accident": (
        "accident de travail déclaration certificat médical employeur Maroc"
    ),
    "contract": (
        "contrat de travail preuve relation de travail CDI CDD Code du travail Maroc"
    ),
    "paid_leave": "congé annuel payé droit congé salarié Code du travail Maroc",
    "sick_leave": "absence maladie certificat médical salarié Code du travail Maroc",
    "overtime": "heures supplémentaires majoration salaire Code du travail Maroc",
    "work_certificate": "certificat de travail remise salarié Code du travail Maroc",
    "preavis": "préavis délai de préavis indemnité préavis Code du travail Maroc",
    "resignation": "démission salarié préavis écrit Code du travail Maroc",
    "labor_inspection": "inspection du travail réclamation salarié employeur Maroc",
}


def _fresh_facts() -> dict[str, str]:
    return deepcopy(DEFAULT_FACTS)


def _has(text_norm: str, terms: tuple[str, ...]) -> bool:
    return any(normalize_text(term) in text_norm for term in terms)


def _has_token(text_norm: str, terms: tuple[str, ...]) -> bool:
    words = set(text_norm.split())
    return any(normalize_text(term) in words for term in terms)


def _has_contract_reference(text_norm: str) -> bool:
    contract_phrases = (
        "بلا عقد",
        "بدون عقد",
        "ما عنديش عقد",
        "ما عنديش كونطرا",
        "ما عطاونيش contrat",
        "ما عطاونيش عقد",
        "ما عطاونيش كونطرا",
        "messages m3a patron",
        "مساجات مع المشغل",
        "nthbet lkhdma",
        "نثبت الخدمة",
        "عقد مكتوب",
        "شفوي",
        "غير شفوي",
        "بلا papier",
        "خدام cash",
        "وقعت ورقة",
        "contrat",
        "contract",
        "cdd",
        "cdi",
        "كونطرا",
    )
    contract_tokens = ("عقد", "العقد")
    return _has(text_norm, contract_phrases) or _has_token(text_norm, contract_tokens)


def _has_cnss_reference(text_norm: str) -> bool:
    cnss_phrases = (
        "cnss",
        "الصندوق الوطني",
        "الضمان الاجتماعي",
        "فالضمان",
        "cotisation",
        "مصرح",
        "مصرحين",
        "مصرحش",
        "مسجل",
        "تصرح",
        "التصريح",
        "صرحو بيا",
        "صرحوا بيا",
    )
    cnss_tokens = ("الضمان", "ضمان")
    return _has(text_norm, cnss_phrases) or _has_token(text_norm, cnss_tokens)


def _add_issues(issues: list[str], *new_issues: str) -> None:
    for issue in new_issues:
        if issue not in issues:
            issues.append(issue)


def _language(question: str) -> str:
    if any("\u0600" <= char <= "\u06ff" for char in question):
        return "darija"
    return "mixed"


def _base_result(question: str) -> dict[str, Any]:
    intent_result = detect_darija_intent(question)
    return {
        "raw_question": question,
        "language": _language(question),
        "intent": intent_result.intent,
        "facts": _fresh_facts(),
        "legal_issues": [],
        "search_query": intent_result.normalized_query or question,
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": float(intent_result.confidence),
    }


def analyze_question(question: str) -> dict[str, Any]:
    """Extract legal meaning from a Darija labor-law question.

    The result is intentionally deterministic: it gives RAG a better legal
    search query and gives the answer prompt facts to respect, without replacing
    source-based retrieval.
    """
    raw_question = (question or "").strip()
    result = _base_result(raw_question)
    facts: dict[str, str] = result["facts"]
    issues: list[str] = result["legal_issues"]
    text = normalize_text(raw_question)

    if not text:
        result.update(
            {
                "intent": "unclear",
                "search_query": "",
                "needs_clarification": True,
                "clarification_question": (
                    "عافاك وضح ليا واش السؤال على الخدمة، الأجر، الطرد، CNSS، "
                    "ولا حادث شغل؟"
                ),
                "confidence": 1.0,
            }
        )
        return result

    if text.startswith("bye") or text.startswith("باي"):
        result.update(
            {
                "intent": "goodbye",
                "search_query": "",
                "needs_clarification": False,
                "clarification_question": None,
                "confidence": max(result["confidence"], 0.95),
            }
        )
        return result

    if _has(text, ("خدام", "خدامة", "اجير", "أجير", "salarié", "salarie")):
        facts["worker_status"] = "employee_claimed"

    if _has_contract_reference(text):
        facts["written_document"] = "contract_or_document_mentioned"
    if _has(text, ("بلا عقد", "ما عنديش عقد", "بدون عقد")):
        facts["written_document"] = "no_written_contract"
    if "cdd" in text:
        facts["contract_type"] = "cdd"
    elif "cdi" in text:
        facts["contract_type"] = "cdi"

    if _has(text, ("رسالة", "مكتوب", "ورقة", "document", "papier")):
        facts["written_document"] = "document_mentioned"
    if _has(text, ("وقعت", "سنيت", "signé", "signe")):
        facts["written_document"] = "signed_document_unknown_content"

    pregnancy_terms = (
        "حامل",
        "حاملة",
        "حمل",
        "الحمل",
        "شهادة حمل",
        "ولادة",
        "الولادة",
        "نولد",
        "ولدت",
        "عطلة الولادة",
        "امومة",
        "أمومة",
        "grossesse",
        "ana 7amla",
        "7amla",
        "maternité",
        "maternite",
    )
    cnss_terms = (
        "cnss",
        "ضمان",
        "الضمان",
        "فالضمان",
        "الضمان الاجتماعي",
        "الصندوق الوطني",
        "cotisation",
        "مصرح",
        "مصرحين",
        "مصرحش",
        "مسجل",
        "تصرح",
        "صرحو بيا",
        "صرحوا بيا",
    )
    accident_terms = (
        "حادث",
        "حادثة",
        "تجرحت",
        "تجرح",
        "تكسرت",
        "طاحت",
        "طحت",
        "طاح",
        "طيحت",
        "تأذيت",
        "تاديت",
        "ضرباتني",
        "machine",
        "t7t f lkhdma",
        "tjre7t",
        "ماكينة",
        "الورشة",
        "accident",
    )
    salary_terms = (
        "خلص",
        "صالير",
        "سالير",
        "أجر",
        "اجر",
        "salaire",
        "اقتطاع",
        "ناقص",
        "ما عطاوني والو",
        "خدمت شهرين",
        "ma khlsonich",
        "khdemt jouj chhor",
        "ma 3tawni walo",
        "khsmo lia",
        "خصمو ليا",
    )
    dismissal_terms = (
        "طرد",
        "طردوني",
        "فصل",
        "خرجوني",
        "خرجني",
        "حيدوني",
        "حيدو",
        "حيدوه",
        "ma tb9ach tji",
        "trdoni",
        "ma tjich ghda",
        "7ydo smiti",
        "sir trta7",
        "7ta n3ayto lik",
        "ما تبقاش تجي",
        "ما تجيش",
        "منعوني",
        "منعني",
        "منعني ندخل",
        "منعني نخدم",
        "مخلاونيش ندخل",
        "ما خلاونيش نخدم",
        "ما قبلونيش نرجع",
        "ما بقاوش كيردو",
        "رجعني",
        "ما خلوونيش نرجع",
        "ما خلوونيش ندخل",
        "قالو ليا",
        "سير بحالك",
        "حتى نعيطو ليك",
        "سير حتى نعيطو ليك",
        "مارجعش",
        "ما ترجعش",
        "سدّو عليا",
        "سدو عليا",
        "fin de contrat",
        "planning بلا تفسير",
        "planning bla tafsir",
        "shift الجديد",
        "البوست",
        "poste",
    )
    vague_dismissal_terms = (
        "ma tb9ach tji",
        "ma tjich ghda",
        "7ydo smiti",
        "sir trta7",
        "7ta n3ayto lik",
        "ما تبقاش تجي",
        "ما تجيش",
        "ما بقاوش كيردو",
        "منعوني ندخل",
        "منعني ندخل",
        "منعني نخدم",
        "مخلاونيش ندخل",
        "ما خلاونيش نخدم",
        "ما قبلونيش نرجع",
        "وقفوني",
        "حتى نعيطو ليك",
        "ما خلوونيش ندخل",
        "ما خلوونيش نرجع",
        "سدّو عليا",
        "سدو عليا",
        "planning بلا تفسير",
        "planning bla tafsir",
        "shift الجديد",
    )
    refused_access_terms = (
        "مخلاونيش ندخل",
        "منعوني ندخل",
        "منعني ندخل",
        "منعني نخدم",
        "ما خلاونيش نخدم",
        "ما قبلونيش نرجع",
    )
    disciplinary_terms = (
        "خطأ جسيم",
        "faute grave",
        "مسطرة تأديبية",
        "استماع",
        "محضر",
        "سرقة",
        "سرقت",
        "اعتراف",
        "غياب غير مبرر",
        "convocation",
        "avertissement",
    )
    labor_inspection_terms = (
        "مفتش الشغل",
        "مفتشية الشغل",
        "تفتيش الشغل",
        "التفتيش",
        "للتفتيش",
        "inspection",
        "inspecteur",
        "mofatich choghl",
        "chikaya 3nd mofatich",
    )
    resignation_terms = (
        "نستاقل",
        "استقالة",
        "استاقل",
        "nsta9el",
        "isti9ala",
        "démission",
        "demission",
        "resignation",
    )
    preavis_terms = (
        "preavis",
        "préavis",
        "انذار",
        "إشعار",
        "اخطار",
        "بقا شهر",
        "شهر آخر",
        "نقطعو عليك",
        "باغي نمشي بلا مشاكل",
    )
    work_certificate_terms = (
        "شهادة العمل",
        "شهادة الشغل",
        "شهادة الخدمة",
        "شهادة ناقصة",
        "certificat de travail",
        "attestation",
        "chahadat l3amal",
        "رفضو يعطوني papier",
        "رفض يعطيني papier",
        "ورقة الخدمة",
    )
    overtime_terms = (
        "سوايع زايدة",
        "ساعات إضافية",
        "الساعات الإضافية",
        "ساعات زايدة",
        "sa3at zayda",
        "kankhdem sa3at zayda",
        "heures sup",
        "overtime",
        "راحة الأسبوعية",
        "حتى 10",
        "10 دالليل",
        "بعد الوقت",
        "weekend",
        "weekends",
        "planning فيه ساعات",
        "أكثر من الوقت العادي",
    )
    sick_leave_terms = (
        "مرض",
        "مرضت",
        "mrdt",
        "طبيب",
        "شهادة طبية",
        "maladie",
        "certificat médical",
        "certificat medical",
        "arrêt",
        "arret",
        "repos",
        "السبيطار",
        "سبيطار",
        "absence",
        "بالمرض",
        "أكثر من أربعة أيام",
        "اكثر من اربعة ايام",
    )
    vague_unclear_terms = ("شي حاجة ماشي واضحة", "ماشي واضحة", "ما فهمتش", "مافهمتش", "بغيت نعرف حقي")
    specific_terms = (
        labor_inspection_terms
        + resignation_terms
        + preavis_terms
        + work_certificate_terms
        + overtime_terms
        + pregnancy_terms
        + accident_terms
        + salary_terms
        + dismissal_terms
        + disciplinary_terms
        + sick_leave_terms
        + ("كونجي", "عطلة", "congé", "conge")
    )

    if (
        _has(text, vague_unclear_terms)
        and not _has(text, specific_terms)
        and not _has_cnss_reference(text)
        and not _has_contract_reference(text)
    ):
        result.update(
            {
                "intent": "unclear",
                "search_query": raw_question,
                "needs_clarification": True,
                "clarification_question": (
                    "عافاك وضح ليا واش المشكل متعلق بالأجر، الطرد، العقد، CNSS، العطلة، المرض، أو حادثة شغل؟"
                ),
                "confidence": max(result["confidence"], 0.7),
            }
        )
        return result

    if _has(text, labor_inspection_terms):
        result["intent"] = "labor_inspection"
        _add_issues(issues, "labor_inspection", "practical_complaint")
        result["search_query"] = SEARCH_QUERIES["labor_inspection"]
        result["confidence"] = max(result["confidence"], 0.84)
        return result

    if _has(text, preavis_terms):
        result["intent"] = "preavis"
        _add_issues(issues, "notice_period", "preavis_indemnity")
        result["search_query"] = SEARCH_QUERIES["preavis"]
        result["confidence"] = max(result["confidence"], 0.82)
        return result

    if _has(text, work_certificate_terms):
        result["intent"] = "work_certificate"
        _add_issues(issues, "work_certificate", "end_of_contract_document")
        result["search_query"] = SEARCH_QUERIES["work_certificate"]
        result["confidence"] = max(result["confidence"], 0.82)
        return result

    if _has(text, ("السالير باقي", "الصالير باقي", "عندي مشكل فالخلصة", "ما تخلصتش،")):
        result["intent"] = "salary_unpaid"
        _add_issues(issues, "salary_payment", "salary_proof", "employer_obligation")
        result["search_query"] = SEARCH_QUERIES["salary_unpaid"]
        result["confidence"] = max(result["confidence"], 0.86)
        return result

    if _has(text, overtime_terms):
        result["intent"] = "overtime"
        _add_issues(issues, "overtime", "weekly_rest", "salary_majoration")
        result["search_query"] = SEARCH_QUERIES["overtime"]
        result["confidence"] = max(result["confidence"], 0.82)
        return result

    if _has(text, refused_access_terms):
        if _has(text, pregnancy_terms):
            result["intent"] = "maternity_protection"
            facts["pregnancy_status"] = "pregnant_or_maternity"
            facts["employer_action"] = "refused_access_after_maternity"
            _add_issues(
                issues,
                "maternity_leave",
                "return_to_work",
                "refused_access_after_maternity",
                "possible_dismissal_after_maternity",
            )
            result["search_query"] = SEARCH_QUERIES["maternity_protection"]
            result["confidence"] = max(result["confidence"], 0.9)
            return result

        result["intent"] = "dismissal_unclear"
        facts["employer_action"] = "blocked_from_workplace"
        _add_issues(
            issues,
            "refused_access_to_workplace",
            "possible_dismissal_or_suspension",
            "written_reason",
            "dismissal_procedure",
        )
        result["search_query"] = SEARCH_QUERIES["dismissal_unclear"]
        result["needs_clarification"] = True
        result["clarification_question"] = "واش عطاوك سبب مكتوب ولا غير منعوك من الدخول؟"
        result["confidence"] = max(result["confidence"], 0.86)
        return result

    if _has(text, pregnancy_terms):
        result["intent"] = "maternity_protection"
        facts["pregnancy_status"] = "pregnant_or_maternity"
        if _has(text, ("شهادة طبية", "certificat", "مثبت", "ثابت")):
            facts["pregnancy_status"] = "medically_confirmed"
        if _has(text, ("رجعت", "بعد الولادة", "رفض يرجعني", "ما قبلونيش")):
            facts["employer_action"] = "refused_return_after_maternity"
        elif _has(text, dismissal_terms):
            facts["employer_action"] = "dismissal_or_threat_during_pregnancy"
        _add_issues(
            issues,
            "maternity_protection",
            "dismissal_during_pregnancy",
            "medical_certificate",
            "return_after_maternity",
        )
        result["search_query"] = SEARCH_QUERIES["maternity_protection"]
        result["confidence"] = max(result["confidence"], 0.9)
        return result

    pressure_resignation = _has(text, ("ضغطو", "ضغط", "كيضغط", "هددوني", "كتب استقالة", "تحت الضغط"))
    if _has(text, resignation_terms) and not (_has(text, pregnancy_terms) and pressure_resignation):
        result["intent"] = "resignation"
        _add_issues(issues, "resignation", "notice_period", "written_proof")
        result["search_query"] = SEARCH_QUERIES["resignation"]
        result["confidence"] = max(result["confidence"], 0.82)
        return result

    if _has_cnss_reference(text):
        result["intent"] = "cnss_non_declaration"
        if _has(text, ("كيشدو", "كيتقطع", "اقتطاع", "cotisation", "ناقص")) and _has(
            text, ("ما مصرح", "ما باين", "ما لقيتش", "مسجلنيش", "غير مصرح")
        ):
            facts["cnss_status"] = "deducted_but_not_declared"
        elif _has(text, ("ما لقيتش", "ما باين", "مسجلنيش", "ما مصرح")):
            facts["cnss_status"] = "not_declared_or_not_visible"
        else:
            facts["cnss_status"] = "cnss_issue_mentioned"
        _add_issues(issues, "cnss_declaration", "salary_deduction", "employer_obligation")
        result["search_query"] = SEARCH_QUERIES["cnss_non_declaration"]
        result["confidence"] = max(result["confidence"], 0.88)
        return result

    if _has(text, accident_terms):
        result["intent"] = "work_accident"
        if _has(text, ("داخل الخدمة", "فالخدمة", "فالعمل", "وانا خدام", "فالمعمل", "الشركة")):
            facts["accident_context"] = "inside_work"
        elif _has(text, ("فالطريق", "للطريق", "غادي للخدمة", "راجع من الخدمة")):
            facts["accident_context"] = "commute_or_work_route"
        else:
            facts["accident_context"] = "work_accident_claimed"
        _add_issues(issues, "accident_de_travail", "declaration", "medical_certificate")
        result["search_query"] = SEARCH_QUERIES["work_accident"]
        result["confidence"] = max(result["confidence"], 0.88)
        return result

    if _has(text, sick_leave_terms):
        result["intent"] = "sick_leave"
        _add_issues(issues, "sick_leave", "medical_certificate", "absence_notice")
        result["search_query"] = SEARCH_QUERIES["sick_leave"]
        result["confidence"] = max(result["confidence"], 0.82)
        return result

    if _has(text, disciplinary_terms):
        result["intent"] = "disciplinary_dismissal"
        facts["employer_action"] = "disciplinary_action_or_fault_allegation"
        _add_issues(issues, "faute_grave", "disciplinary_procedure", "right_to_be_heard")
        result["search_query"] = SEARCH_QUERIES["disciplinary_dismissal"]
        result["confidence"] = max(result["confidence"], 0.84)
        return result

    if _has(text, dismissal_terms):
        is_vague = _has(text, vague_dismissal_terms)
        result["intent"] = "dismissal_unclear" if is_vague else "dismissal"
        if _has(text, ("ما تبقاش تجي", "قالو ليا")):
            facts["employer_action"] = "told_not_to_return"
        elif _has(text, ("منعوني", "منعني", "ما خلوونيش ندخل")):
            facts["employer_action"] = "blocked_from_workplace"
        elif _has(text, ("وقفوني", "suspension")):
            facts["employer_action"] = "temporary_suspension_or_unclear_stop"
        else:
            facts["employer_action"] = "dismissal_claimed"
        _add_issues(issues, "dismissal_or_suspension", "dismissal_procedure", "written_reason")
        result["search_query"] = SEARCH_QUERIES[result["intent"]]
        result["needs_clarification"] = is_vague
        if is_vague:
            result["clarification_question"] = "واش عطاوك سبب مكتوب ولا غير قالوها ليك شفوي؟"
        result["confidence"] = max(result["confidence"], 0.82 if is_vague else 0.86)
        return result

    if _has(text, salary_terms):
        result["intent"] = "salary_unpaid"
        if _has(
            text,
            (
                "ما خلص",
                "ما تخلص",
                "ما عطانيش",
                "ما عطاوني والو",
                "ma khlsonich",
                "ma 3tawni walo",
                "باقي",
            ),
        ):
            facts["salary_status"] = "unpaid"
        elif _has(text, ("ناقص", "نقص", "اقتطاع", "قطعو")):
            facts["salary_status"] = "underpaid_or_deducted"
        else:
            facts["salary_status"] = "salary_issue_mentioned"
        _add_issues(issues, "salary_payment", "salary_proof", "employer_obligation")
        result["search_query"] = SEARCH_QUERIES["salary_unpaid"]
        result["confidence"] = max(result["confidence"], 0.86)
        return result

    if _has_contract_reference(text):
        result["intent"] = "contract"
        _add_issues(issues, "employment_contract", "proof_of_work_relation", "contract_type")
        result["search_query"] = SEARCH_QUERIES["contract"]
        result["confidence"] = max(result["confidence"], 0.8)
        return result

    if _has(text, ("كونجي", "عطلة", "congé", "conge")):
        result["intent"] = "paid_leave"
        _add_issues(issues, "annual_leave", "paid_leave_entitlement")
        result["search_query"] = SEARCH_QUERIES["paid_leave"]
        result["confidence"] = max(result["confidence"], 0.78)
        return result

    if _has(text, ("مرض", "طبيب", "شهادة طبية", "maladie", "certificat")):
        result["intent"] = "sick_leave"
        _add_issues(issues, "sick_leave", "medical_certificate", "absence_notice")
        result["search_query"] = SEARCH_QUERIES["sick_leave"]
        result["confidence"] = max(result["confidence"], 0.78)
        return result

    if _has(text, ("سوايع زايدة", "ساعات إضافية", "heures sup", "overtime", "راحة الأسبوعية")):
        result["intent"] = "overtime"
        _add_issues(issues, "overtime", "weekly_rest", "salary_majoration")
        result["search_query"] = SEARCH_QUERIES["overtime"]
        result["confidence"] = max(result["confidence"], 0.78)
        return result

    if _has(text, ("شهادة العمل", "شهادة الشغل", "certificat de travail")):
        result["intent"] = "work_certificate"
        _add_issues(issues, "work_certificate", "end_of_contract_document")
        result["search_query"] = SEARCH_QUERIES["work_certificate"]
        result["confidence"] = max(result["confidence"], 0.78)
        return result

    if _has(text, ("preavis", "préavis", "انذار", "إشعار", "اخطار")):
        result["intent"] = "preavis"
        _add_issues(issues, "notice_period", "preavis_indemnity")
        result["search_query"] = SEARCH_QUERIES["preavis"]
        result["confidence"] = max(result["confidence"], 0.78)
        return result

    if _has(text, ("نستاقل", "استقالة", "استاقل", "démission", "demission")):
        result["intent"] = "resignation"
        _add_issues(issues, "resignation", "notice_period", "written_proof")
        result["search_query"] = SEARCH_QUERIES["resignation"]
        result["confidence"] = max(result["confidence"], 0.76)
        return result

    if _has(text, ("مفتش الشغل", "تفتيش الشغل", "inspection", "inspecteur")):
        result["intent"] = "labor_inspection"
        _add_issues(issues, "labor_inspection", "practical_complaint")
        result["search_query"] = SEARCH_QUERIES["labor_inspection"]
        result["confidence"] = max(result["confidence"], 0.74)
        return result

    if result["intent"] in {"unclear", "out_of_scope"}:
        result["confidence"] = max(result["confidence"], 0.3)
        return result

    result["search_query"] = result["search_query"] or raw_question
    return result

"""Citation-span verification — the deepest-tested capability (Phase 2).

The point of these tests is that a *bad* citation cannot silently pass. Each adversarial failure mode has a test that
would fail if the verifier stopped catching it:

  - fabricated span (not in context)              -> provenance fails
  - cited-but-unsupported / wrong span            -> support fails
  - right answer, wrong citation                  -> support fails (a correct answer with a bad cite still fails)
  - uncited claim                                 -> fails when a citation is required
  - a genuinely valid citation                    -> passes
  - partial (one good, one bad)                   -> fraction < 1.0, case fails by default

Plus the documented boundary: lexical support is a proxy, not entailment (a contradiction it cannot see).
"""
from __future__ import annotations

import spancheck
from spancheck import Case, evaluate, verify_citation, citation_accuracy
from spancheck.adapter import Output

CTX = [
    "Either party may terminate the agreement with 30 days written notice.",
    "Invoices are payable within 45 days of receipt.",
]


# ---------------- verify_citation: the two checks, in isolation ----------------
def test_valid_citation_passes_both_checks():
    v = verify_citation(
        {"span": "terminate the agreement with 30 days written notice",
         "claim": "Either party may terminate the agreement with 30 days written notice"},
        CTX)
    assert v.span_found and v.claim_supported and v.ok


def test_fabricated_span_fails_provenance():
    v = verify_citation("the penalty for late payment is five hundred dollars", CTX,
                        answer="There is a $500 late penalty.")
    assert v.span_found is False and v.ok is False
    assert "fabricated" in v.reason


def test_wrong_span_real_but_unsupporting_fails_support():
    # the span is real (present in CTX) but is about invoices, not termination
    v = verify_citation(
        {"span": "Invoices are payable within 45 days of receipt",
         "claim": "Either party may terminate the agreement with 30 days written notice"},
        CTX)
    assert v.span_found is True          # provenance holds — it IS in the context
    assert v.claim_supported is False    # but it doesn't support the termination claim
    assert v.ok is False


def test_right_answer_wrong_citation_still_fails():
    # answer is correct, but the cited span points at the wrong sentence -> a citation failure
    out = Output(
        answer="Either party may terminate with 30 days written notice.",
        contexts=CTX,
        citations=[{"span": "Invoices are payable within 45 days of receipt",
                    "claim": "Either party may terminate with 30 days written notice"}],
    )
    grade = citation_accuracy()(Case("c", "q", meta={"answerable": True}), out)
    assert grade.passed is False and grade.score == 0.0


def test_empty_span_fails():
    v = verify_citation({"span": "   "}, CTX, answer="something")
    assert v.ok is False and "empty" in v.reason


# ---------------- source-scoped provenance (a citation attributed to the wrong document) ----------------
_SOURCES = {
    "MSA": "Either party may terminate the agreement with 30 days written notice.",
    "Invoicing Policy": "Invoices are payable within 45 days of receipt.",
}


def test_citation_scoped_to_the_right_source_passes():
    v = verify_citation(
        {"span": "Either party may terminate the agreement with 30 days written notice",
         "claim": "Either party may terminate with 30 days written notice", "source_id": "MSA"},
        contexts=list(_SOURCES.values()), sources=_SOURCES)
    assert v.scoped is True and v.span_found is True and v.ok is True


def test_citation_attributed_to_wrong_source_fails_even_though_span_is_real():
    # the span is real and present in the corpus, but it is NOT in the source the citation names
    v = verify_citation(
        {"span": "Invoices are payable within 45 days of receipt",
         "claim": "Invoices are payable within 45 days", "source_id": "MSA"},  # wrong doc
        contexts=list(_SOURCES.values()), sources=_SOURCES)
    assert v.scoped is True
    assert v.span_found is False          # not found in its CITED source (the MSA)
    assert v.ok is False and "misattributed" in v.reason


def test_unscoped_when_no_sources_falls_back_to_all_contexts():
    v = verify_citation(
        {"span": "Invoices are payable within 45 days of receipt", "claim": "Invoices are payable within 45 days",
         "source_id": "MSA"},
        contexts=list(_SOURCES.values()))  # no sources map -> can't scope -> checks all contexts
    assert v.scoped is False and v.span_found is True


def test_bare_string_citation_is_accepted_as_a_span():
    v = verify_citation("Either party may terminate the agreement with 30 days written notice", CTX,
                        answer="Either party may terminate the agreement with 30 days written notice")
    assert v.span_found and v.ok


# ---------------- normalisation ----------------
def test_provenance_is_whitespace_and_case_insensitive():
    v = verify_citation("TERMINATE   the   AGREEMENT with 30 days written notice", CTX,
                        answer="terminate the agreement with 30 days written notice")
    assert v.span_found is True


def test_paraphrased_citation_is_not_matched_by_design():
    # a paraphrase (not a verbatim quote) must fail provenance — a deliberate incentive to quote sources exactly
    v = verify_citation("both sides can end the contract with a month's notice", CTX,
                        answer="both sides can end the contract with a month's notice")
    assert v.span_found is False


# ---------------- the documented proxy boundary ----------------
def test_lexical_support_is_a_proxy_not_entailment():
    # A span that shares the claim's words but CONTRADICTS it. The lexical proxy CANNOT see the negation and
    # (given provenance) treats it as supported. This is a known, documented limit (AB-DEC 007) and the reason
    # the calibrated LLM-judge exists in Phase 4. The test pins the boundary so it is explicit, not hidden.
    ctx = ["The notice period is not 30 days under the amended terms."]
    v = verify_citation(
        {"span": "The notice period is not 30 days under the amended terms",
         "claim": "The notice period is 30 days"},
        ctx)
    assert v.span_found is True
    assert v.claim_supported is True   # <-- the proxy's blind spot: negation is invisible to lexical overlap
    assert v.ok is True                #     Phase 4's judge is what upgrades this to true entailment.


# ---------------- the grader, through evaluate + the default set ----------------
def valid_system(q):
    return {"answer": "Either party may terminate with 30 days written notice.",
            "contexts": CTX,
            "citations": [{"span": "Either party may terminate the agreement with 30 days written notice",
                           "claim": "Either party may terminate with 30 days written notice"}]}


def fabricating_system(q):
    return {"answer": "There is a $500 late-payment penalty.",
            "contexts": CTX,
            "citations": ["the penalty for late payment is five hundred dollars"]}


def uncited_system(q):
    return {"answer": "Either party may terminate with 30 days notice.", "contexts": CTX}  # no citations


def abstaining_system(q):
    return {"answer": "I don't know — that isn't in the document.", "contexts": CTX}


def test_valid_system_scores_citation_accuracy_1():
    sc = evaluate([Case("c", "q", meta={"answerable": True})], valid_system).scorecard().by_grader()
    assert sc["citation_accuracy"]["pass_rate"] == 1.0


def test_fabricating_system_fails_citation_accuracy():
    sc = evaluate([Case("c", "q", meta={"answerable": True})], fabricating_system).scorecard().by_grader()
    assert sc["citation_accuracy"]["pass_rate"] == 0.0


def test_uncited_answer_fails_by_default_but_passes_when_not_required():
    case = Case("c", "q", meta={"answerable": True})
    strict = evaluate([case], uncited_system).scorecard().by_grader()
    assert strict["citation_accuracy"]["pass_rate"] == 0.0
    lenient = evaluate([case], uncited_system, graders=[citation_accuracy(require_citation=False)]) \
        .scorecard().by_grader()
    assert lenient["citation_accuracy"]["pass_rate"] == 1.0


def test_abstention_passes_citation_accuracy_trivially():
    sc = evaluate([Case("c", "q", meta={"answerable": False})], abstaining_system).scorecard().by_grader()
    assert sc["citation_accuracy"]["pass_rate"] == 1.0


def test_partial_citations_score_a_fraction_and_fail_all_or_nothing():
    def half_good_system(q):
        return {"answer": "Termination needs 30 days notice; invoices due in 45 days.",
                "contexts": CTX,
                "citations": [
                    # valid: a real span, scoped to the claim it supports
                    {"span": "Either party may terminate the agreement with 30 days written notice",
                     "claim": "termination needs 30 days written notice"},
                    "a completely fabricated clause about penalties",  # fabricated -> fails provenance
                ]}
    grade = citation_accuracy()(Case("c", "q", meta={"answerable": True}), spancheck.normalize(half_good_system("q")))
    assert grade.score == 0.5 and grade.passed is False


def test_citation_accuracy_in_default_grader_set():
    # default_graders must now include citation accuracy
    names = {g.grader for g in
             [gr(Case("c", "q", meta={"answerable": True}), spancheck.normalize(valid_system("q")))
              for gr in spancheck.default_graders()]}
    assert "citation_accuracy" in names

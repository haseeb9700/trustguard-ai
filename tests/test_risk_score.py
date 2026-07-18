"""Tests for rule-based risk scoring and claim-level escalation."""

from modules.risk_score import apply_claim_escalation, calculate_risk


class TestCalculateRisk:
    def test_grounded_answer_is_low_risk(self):
        risk = calculate_risk({"hallucination_score": 0}, "The policy lasts 14 days.")
        assert risk["risk_level"] == "Low"
        assert risk["risk_status"] == "Grounded"

    def test_partial_hallucination_is_medium_risk(self):
        risk = calculate_risk({"hallucination_score": 1}, "Some answer.")
        assert risk["risk_level"] == "Medium"

    def test_major_hallucination_is_high_risk(self):
        risk = calculate_risk({"hallucination_score": 2}, "Some answer.")
        assert risk["risk_level"] == "High"

    def test_unverified_answer_is_medium_risk(self):
        risk = calculate_risk(
            {"hallucination_score": 0},
            "I could not verify this from the provided sources.",
        )
        assert risk["risk_level"] == "Medium"
        assert risk["risk_status"] == "Unverified"

    def test_json_string_analysis_is_parsed(self):
        risk = calculate_risk('{"hallucination_score": 0}', "Answer.")
        assert risk["risk_level"] == "Low"

    def test_malformed_analysis_defaults_to_high_risk(self):
        risk = calculate_risk("not json at all", "Answer.")
        assert risk["risk_level"] == "High"

    def test_missing_score_defaults_to_high_risk(self):
        risk = calculate_risk({}, "Answer.")
        assert risk["risk_level"] == "High"


class TestClaimEscalation:
    LOW = {"risk_score": 0, "risk_level": "Low", "risk_status": "Grounded", "risk_reason": "ok"}
    HIGH = {"risk_score": 2, "risk_level": "High", "risk_status": "Unsupported", "risk_reason": "bad"}

    def test_contradicted_claim_forces_high_risk(self):
        claims = [{"verdict": "entailed"}, {"verdict": "contradicted"}]
        risk = apply_claim_escalation(dict(self.LOW), claims)
        assert risk["risk_level"] == "High"
        assert risk["risk_status"] == "Contradicted"

    def test_baseless_claim_raises_floor_to_medium(self):
        claims = [{"verdict": "entailed"}, {"verdict": "baseless"}]
        risk = apply_claim_escalation(dict(self.LOW), claims)
        assert risk["risk_level"] == "Medium"

    def test_all_entailed_keeps_original_risk(self):
        claims = [{"verdict": "entailed"}, {"verdict": "entailed"}]
        risk = apply_claim_escalation(dict(self.LOW), claims)
        assert risk["risk_level"] == "Low"

    def test_never_downgrades_high_risk(self):
        claims = [{"verdict": "baseless"}]
        risk = apply_claim_escalation(dict(self.HIGH), claims)
        assert risk["risk_level"] == "High"

    def test_empty_claims_keep_original_risk(self):
        risk = apply_claim_escalation(dict(self.LOW), [])
        assert risk["risk_level"] == "Low"

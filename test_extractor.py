"""
Tests for Melusina BC Extractor — 5 required examples + edge cases.
Run: python3 -m pytest test_extractor.py -v
"""

import json
import tempfile
from pathlib import Path

import pytest

from extractor import (
    ConstitutionWriter,
    Extractor,
    JfpRule,
    RuleClass,
    RuleGenerator,
    Section,
    SignalDetector,
    SignalType,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_constitution(tmp_path: Path) -> Path:
    """Returns a fresh temporary constitution file path."""
    return tmp_path / "constitution.jfp"


@pytest.fixture
def extractor(tmp_constitution: Path) -> Extractor:
    """Extractor wired to a temp constitution (no ~/.jfp pollution)."""
    return Extractor(constitution_path=tmp_constitution)


@pytest.fixture
def detector() -> SignalDetector:
    return SignalDetector()


@pytest.fixture
def generator() -> RuleGenerator:
    return RuleGenerator()

# ── Helper ────────────────────────────────────────────────────────────────────

def run(extractor: Extractor, message: str) -> JfpRule | None:
    """Process without interactive confirmation."""
    return extractor.process(message, confirm=False)

# ══════════════════════════════════════════════════════════════════════════════
# Required test cases (5 examples from the spec)
# ══════════════════════════════════════════════════════════════════════════════

class TestRequiredExamples:

    def test_1_explicit_always_polish(self, extractor: Extractor, tmp_constitution: Path):
        """
        Example 1 — EXPLICIT signal: 'od teraz zawsze odpowiadaj po polsku'
        Expected: BEHAVIORAL_RULES / ALPHA / explicit
        """
        msg  = "od teraz zawsze odpowiadaj po polsku"
        rule = run(extractor, msg)

        assert rule is not None, "Should detect a rule"
        assert rule.section == Section.BEHAVIORAL_RULES.value
        assert rule.cls     == RuleClass.ALPHA.value
        assert rule.source  == SignalType.EXPLICIT.value
        assert rule.key     == "RULE_001"

        # Verify persisted to file
        saved = json.loads(tmp_constitution.read_text().strip())
        assert saved["key"]     == "RULE_001"
        assert saved["section"] == "BEHAVIORAL_RULES"

    def test_2_explicit_never_emoji(self, extractor: Extractor):
        """
        Example 2 — EXPLICIT signal: 'nigdy nie używaj emoji w odpowiedziach'
        Expected: BEHAVIORAL_RULES / ALPHA / explicit
        """
        msg  = "nigdy nie używaj emoji w odpowiedziach"
        rule = run(extractor, msg)

        assert rule is not None
        assert rule.section == Section.BEHAVIORAL_RULES.value
        assert rule.cls     == RuleClass.ALPHA.value
        assert rule.source  == SignalType.EXPLICIT.value
        assert "emoji" in rule.value.lower() or "używaj" in rule.value.lower()

    def test_3_explicit_remember_project_name(self, extractor: Extractor):
        """
        Example 3 — EXPLICIT/PRIORITIES: 'pamiętaj że nasz projekt nazywa się VIKI'
        Expected: PRIORITIES / BETA / explicit
        """
        msg  = "pamiętaj że nasz projekt nazywa się VIKI"
        rule = run(extractor, msg)

        assert rule is not None
        assert rule.section == Section.PRIORITIES.value
        assert rule.cls     == RuleClass.BETA.value
        assert rule.source  == SignalType.EXPLICIT.value
        assert "VIKI" in rule.value

    def test_4_domain_lora_terminology(self, extractor: Extractor):
        """
        Example 4 — DOMAIN signal: 'to się nazywa LoRA nie LORA'
        Expected: DOMAIN_KNOWLEDGE / GAMMA / domain
        """
        msg  = "to się nazywa LoRA nie LORA"
        rule = run(extractor, msg)

        assert rule is not None
        assert rule.section == Section.DOMAIN_KNOWLEDGE.value
        assert rule.cls     == RuleClass.GAMMA.value
        assert rule.source  == SignalType.DOMAIN.value
        assert "LoRA" in rule.value or "LORA" in rule.value

    def test_5_implicit_terminology_correction(self, extractor: Extractor):
        """
        Example 5 — 'nie mów fine-tuning, mówimy dostrajanie'
        Updated: now correctly classified as DOMAIN (terminology replacement),
        not IMPLICIT. The new DOMAIN pattern takes priority over generic IMPLICIT.
        Expected: DOMAIN_KNOWLEDGE / GAMMA / domain
        """
        msg  = "nie mów 'fine-tuning', mówimy 'dostrajanie'"
        rule = run(extractor, msg)

        assert rule is not None
        assert rule.section == Section.DOMAIN_KNOWLEDGE.value
        assert rule.cls     == RuleClass.GAMMA.value
        assert rule.source  == SignalType.DOMAIN.value

# ══════════════════════════════════════════════════════════════════════════════
# Additional edge-case tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSignalDetector:

    def test_no_signal_returns_none(self, detector: SignalDetector):
        assert detector.detect("Jaka jest stolica Francji?") is None

    def test_english_always(self, detector: SignalDetector):
        sig = detector.detect("always respond in English")
        assert sig is not None
        assert sig.signal_type == SignalType.EXPLICIT
        assert sig.rule_class  == RuleClass.ALPHA

    def test_english_never(self, detector: SignalDetector):
        sig = detector.detect("never use markdown headers")
        assert sig is not None
        assert sig.signal_type == SignalType.EXPLICIT

    def test_english_remember(self, detector: SignalDetector):
        sig = detector.detect("remember that my name is Jaro")
        assert sig is not None
        assert sig.signal_type == SignalType.EXPLICIT
        assert sig.section     == Section.PRIORITIES

    def test_domain_we_call_it(self, detector: SignalDetector):
        sig = detector.detect("we call it 'adapter' not 'plugin'")
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN

    def test_implicit_wrong(self, detector: SignalDetector):
        sig = detector.detect("wrong, the answer should be 42")
        assert sig is not None
        assert sig.signal_type == SignalType.IMPLICIT


class TestRuleGenerator:

    def test_key_format(self, generator: RuleGenerator, detector: SignalDetector):
        msg = "od teraz odpowiadaj zwięźle"
        sig = detector.detect(msg)
        rule = generator.generate(msg, sig, "RULE_007")
        assert rule.key == "RULE_007"

    def test_value_not_empty(self, generator: RuleGenerator, detector: SignalDetector):
        msg = "zawsze używaj polskich znaków"
        sig = detector.detect(msg)
        rule = generator.generate(msg, sig, "RULE_001")
        assert rule.value.strip() != ""

    def test_to_dict_has_all_fields(self, generator: RuleGenerator, detector: SignalDetector):
        msg = "pamiętaj że preferuję krótkie odpowiedzi"
        sig = detector.detect(msg)
        rule = generator.generate(msg, sig, "RULE_001")
        d = rule.to_dict()
        for field in ("section", "key", "value", "class", "source", "timestamp"):
            assert field in d, f"Missing field: {field}"


class TestConstitutionWriter:

    def test_creates_file_on_first_write(self, tmp_constitution: Path):
        writer = ConstitutionWriter(tmp_constitution)
        rule = JfpRule(
            section="BEHAVIORAL_RULES", key="RULE_001",
            value="Test rule", cls="ALPHA", source="explicit"
        )
        writer.append(rule)
        assert tmp_constitution.exists()

    def test_next_key_empty_file(self, tmp_constitution: Path):
        writer = ConstitutionWriter(tmp_constitution)
        assert writer.next_key() == "RULE_001"

    def test_next_key_increments(self, tmp_constitution: Path):
        writer = ConstitutionWriter(tmp_constitution)
        for i in range(3):
            writer.append(JfpRule(
                section="BEHAVIORAL_RULES", key=f"RULE_{i+1:03d}",
                value=f"Rule {i+1}", cls="BETA", source="explicit"
            ))
        assert writer.next_key() == "RULE_004"

    def test_jsonl_format(self, tmp_constitution: Path):
        writer = ConstitutionWriter(tmp_constitution)
        writer.append(JfpRule(
            section="PRIORITIES", key="RULE_001",
            value="Test", cls="BETA", source="explicit"
        ))
        lines = tmp_constitution.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["key"] == "RULE_001"


class TestExtractorPipeline:

    def test_multiple_rules_sequential_keys(self, extractor: Extractor):
        run(extractor, "od teraz odpowiadaj po polsku")
        run(extractor, "nigdy nie używaj tabelek")
        run(extractor, "pamiętaj że projekt to VIKI")

        rules = extractor.writer.load_all()
        assert len(rules) == 3
        assert rules[0]["key"] == "RULE_001"
        assert rules[1]["key"] == "RULE_002"
        assert rules[2]["key"] == "RULE_003"

    def test_no_signal_writes_nothing(self, extractor: Extractor, tmp_constitution: Path):
        run(extractor, "Ile to jest 2+2?")
        assert not tmp_constitution.exists() or tmp_constitution.read_text().strip() == ""

    def test_rule_dict_structure(self, extractor: Extractor):
        rule = run(extractor, "zawsze formatuj kod w blokach")
        assert rule is not None
        d = rule.to_dict()
        assert d["section"] in ("BEHAVIORAL_RULES", "DOMAIN_KNOWLEDGE", "PRIORITIES")
        assert d["class"]   in ("ALPHA", "BETA", "GAMMA")
        assert d["source"]  in ("explicit", "implicit", "domain")
        assert d["key"].startswith("RULE_")
        assert "T" in d["timestamp"]  # ISO8601 check


# ══════════════════════════════════════════════════════════════════════════════
# New DOMAIN pattern tests — "nie mów X, mówimy Y" and variants
# ══════════════════════════════════════════════════════════════════════════════

class TestDomainPatternsExtended:
    """Tests for the 4 new DOMAIN patterns added to extractor.py."""

    def test_nie_mow_mowimy(self, detector: SignalDetector, extractor: Extractor):
        """'nie mów fine-tuning, mówimy dostrajanie' → DOMAIN / GAMMA"""
        msg = "nie mów 'fine-tuning', mówimy 'dostrajanie'"
        sig = detector.detect(msg)
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN, \
            f"Expected DOMAIN, got {sig.signal_type} (matched: '{sig.matched_pattern}')"
        assert sig.section    == Section.DOMAIN_KNOWLEDGE
        assert sig.rule_class == RuleClass.GAMMA

        rule = run(extractor, msg)
        assert rule is not None
        assert rule.source  == SignalType.DOMAIN.value
        assert rule.section == Section.DOMAIN_KNOWLEDGE.value

    def test_nie_mow_mowi_sie(self, detector: SignalDetector):
        """'nie mów GPU, mówi się karta graficzna' → DOMAIN"""
        sig = detector.detect("nie mów GPU, mówi się karta graficzna")
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN

    def test_nie_nazywaj_to_jest(self, detector: SignalDetector, extractor: Extractor):
        """'nie nazywaj tego modelem, to jest agent' → DOMAIN / GAMMA"""
        msg = "nie nazywaj tego modelem, to jest agent"
        sig = detector.detect(msg)
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN, \
            f"Expected DOMAIN, got {sig.signal_type}"
        assert sig.section    == Section.DOMAIN_KNOWLEDGE

        rule = run(extractor, msg)
        assert rule is not None
        assert rule.source == SignalType.DOMAIN.value

    def test_nie_nazywaj_to_sie_nazywa(self, detector: SignalDetector):
        """'nie nazywaj tego pluginem, to się nazywa adapter' → DOMAIN"""
        sig = detector.detect("nie nazywaj tego pluginem, to się nazywa adapter")
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN

    def test_zamiast_uzywaj(self, detector: SignalDetector, extractor: Extractor):
        """'zamiast fine-tuning używaj dostrajanie' → DOMAIN / GAMMA"""
        msg = "zamiast fine-tuning używaj dostrajanie"
        sig = detector.detect(msg)
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN, \
            f"Expected DOMAIN, got {sig.signal_type}"

        rule = run(extractor, msg)
        assert rule is not None
        assert rule.source  == SignalType.DOMAIN.value
        assert rule.section == Section.DOMAIN_KNOWLEDGE.value
        assert rule.cls     == RuleClass.GAMMA.value

    def test_zamiast_mow(self, detector: SignalDetector):
        """'zamiast API mów interfejs' → DOMAIN"""
        sig = detector.detect("zamiast API mów interfejs")
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN

    def test_zamiast_stosuj(self, detector: SignalDetector):
        """'zamiast pętli for stosuj list comprehension' → DOMAIN"""
        sig = detector.detect("zamiast pętli for stosuj list comprehension")
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN

    def test_przestan_mowic_chodzi_o(self, detector: SignalDetector, extractor: Extractor):
        """'przestań mówić model, chodzi o agenta' → DOMAIN / GAMMA"""
        msg = "przestań mówić model, chodzi o agenta"
        sig = detector.detect(msg)
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN, \
            f"Expected DOMAIN, got {sig.signal_type}"

        rule = run(extractor, msg)
        assert rule is not None
        assert rule.source == SignalType.DOMAIN.value

    def test_przestan_uzywac_mam_na_mysli(self, detector: SignalDetector):
        """'przestań używać tego słowa, mam na myśli coś innego' → DOMAIN"""
        sig = detector.detect("przestań używać tego słowa, mam na myśli coś innego")
        assert sig is not None
        assert sig.signal_type == SignalType.DOMAIN

    def test_domain_takes_priority_over_implicit(self, detector: SignalDetector):
        """
        'nie mów X, mówimy Y' must be classified as DOMAIN not IMPLICIT.
        The DOMAIN pattern must appear before the generic IMPLICIT 'nie mów' pattern.
        """
        for msg in [
            "nie mów 'fine-tuning', mówimy 'dostrajanie'",
            "nie mów GPU, mówi się karta graficzna",
            "zamiast LLM używaj model językowy",
            "nie nazywaj tego pluginem, to się nazywa adapter",
        ]:
            sig = detector.detect(msg)
            assert sig is not None
            assert sig.signal_type == SignalType.DOMAIN, \
                f"'{msg}' → expected DOMAIN, got {sig.signal_type} (matched: '{sig.matched_pattern}')"

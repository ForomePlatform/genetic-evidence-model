"""Unit tests for the three SHACL conditional-activation shapes.

Each enforced rule is tested in both directions, as the paper's
Reproducibility and Conformance section advertises: an instance whose
activation condition holds but whose dimension is absent is reported as a
violation, and satisfying the dimension (or using the documented
NOT_APPLICABLE_OR_OMITTED escape) clears that violation. Assertions match
on the shapes' sh:message texts, so unrelated base-shape violations of the
deliberately minimal instances do not interfere.

Also validates one full released annotation end-to-end (the same pipeline
as ``gem-validate``).
"""
import tempfile
import unittest
from pathlib import Path

import rdflib
import yaml
from pyshacl import validate

from forome.gem.validation.validate_annotations import BASE, SHACL, y2r

MSG_VA = "variant_ascertainment is required"
MSG_MOI = "mode_of_inheritance is required"
MSG_ORG = "organism is required"


def report(item: dict) -> str:
    """Validation-report text for a document containing one evidence item."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "case.yaml"
        p.write_text(yaml.safe_dump({"evidence": [item]}, sort_keys=False))
        data = rdflib.Graph().parse(data=y2r.convert(p), format="turtle")
    data.parse(SHACL)  # merge enum/class declarations so sh:class resolves
    _, _, text = validate(data, shacl_graph=SHACL, advanced=True)
    return text


class TestVariantAscertainmentRule(unittest.TestCase):
    def test_fires_when_condition_holds_and_dimension_absent(self):
        self.assertIn(MSG_VA, report({"id": "T1", "target_type": "VARIANT"}))

    def test_cleared_by_population(self):
        self.assertNotIn(MSG_VA, report({
            "id": "T1", "target_type": "VARIANT",
            "variant_ascertainment": ["OBSERVED_IN_CASES"]}))

    def test_cleared_by_documented_sentinel(self):
        # The explicit escape for e.g. polygenic scores (CE-IN1).
        self.assertNotIn(MSG_VA, report({
            "id": "T1", "target_type": "VARIANT",
            "variant_ascertainment": ["NOT_APPLICABLE_OR_OMITTED"]}))

    def test_silent_when_condition_does_not_hold(self):
        self.assertNotIn(MSG_VA, report({"id": "T1", "target_type": "GENE"}))


class TestModeOfInheritanceRule(unittest.TestCase):
    COND = {"id": "T1", "knowledge_domain": ["HUMAN_GENETICS"],
            "target_type": "GENE"}

    def test_fires_when_condition_holds_and_dimension_absent(self):
        self.assertIn(MSG_MOI, report(dict(self.COND)))

    def test_cleared_by_population(self):
        self.assertNotIn(MSG_MOI, report(
            {**self.COND, "mode_of_inheritance": "AUTOSOMAL_DOMINANT"}))

    def test_silent_when_conjunction_incomplete(self):
        # HUMAN_GENETICS alone (target VARIANT) must not trigger the rule.
        self.assertNotIn(MSG_MOI, report(
            {"id": "T1", "knowledge_domain": ["HUMAN_GENETICS"],
             "target_type": "VARIANT",
             "variant_ascertainment": ["NOT_APPLICABLE_OR_OMITTED"]}))


class TestOrganismRule(unittest.TestCase):
    def test_fires_on_in_vivo_disjunct(self):
        self.assertIn(MSG_ORG, report({"id": "T1", "method": ["IN_VIVO"]}))

    def test_fires_on_model_organism_disjunct(self):
        self.assertIn(MSG_ORG, report(
            {"id": "T1", "knowledge_domain": ["MODEL_ORGANISM"]}))

    def test_cleared_by_population(self):
        self.assertNotIn(MSG_ORG, report(
            {"id": "T1", "method": ["IN_VIVO"], "organism": ["MOUSE"]}))

    def test_silent_when_condition_does_not_hold(self):
        self.assertNotIn(MSG_ORG, report(
            {"id": "T1", "method": ["IN_VITRO"]}))


class TestReleasedCorpusMember(unittest.TestCase):
    def test_full_annotation_conforms(self):
        """One released annotation validates end-to-end (gem-validate path)."""
        p = BASE / "annotations" / "jossin2017.yaml"
        if not p.is_file():
            self.skipTest("no repo corpus")
        data = rdflib.Graph().parse(data=y2r.convert(p), format="turtle")
        data.parse(SHACL)
        conforms, _, text = validate(data, shacl_graph=SHACL, advanced=True)
        self.assertTrue(conforms, text)


if __name__ == "__main__":
    unittest.main()

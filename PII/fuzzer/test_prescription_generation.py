import unittest

from korean_pii_fuzzer_v4 import FuzzerV4
from korean_pii_output_fuzzer_v4 import OutputFuzzerV4, _gen_bundle_healthcare
from prescription_corpus import (
    DIAGNOSIS_TO_PRESCRIPTION_DRUGS,
    PRESCRIPTION_RULES,
    gen_prescription,
    gen_prescription_for_diagnosis,
    gen_prescription_record,
    is_valid_prescription_fragment,
    resolve_prescription_record,
)
from prescription_mutations import build_prescription_korean_mutations


class PrescriptionGenerationTests(unittest.TestCase):
    def test_generated_prescription_records_stay_inside_rule_table(self):
        for _ in range(500):
            record = gen_prescription_record()
            rule = PRESCRIPTION_RULES[record["drug"]]

            self.assertIn(record["dose"], rule["doses"])
            self.assertIn(record["route"], rule["routes"])
            self.assertIn(record["frequency"], rule["frequencies"])
            self.assertIn(record["method"], rule["methods"])
            self.assertIn(record["supply"], rule["supplies"])
            self.assertIn(record["diagnosis"], rule["diagnoses"])
            self.assertTrue(is_valid_prescription_fragment(record["fragment"], record["diagnosis"]))
            self.assertEqual(resolve_prescription_record(record["fragment"], record["diagnosis"])["drug"], record["drug"])

    def test_diagnosis_specific_generation_uses_allowed_drugs(self):
        for diagnosis, drugs in DIAGNOSIS_TO_PRESCRIPTION_DRUGS.items():
            fragment = gen_prescription_for_diagnosis(diagnosis)
            resolved = resolve_prescription_record(fragment, diagnosis)

            self.assertIsNotNone(resolved, f"unresolved prescription for {diagnosis}: {fragment}")
            self.assertIn(resolved["drug"], drugs)
            self.assertTrue(is_valid_prescription_fragment(fragment, diagnosis))

    def test_invalid_drug_dose_combination_is_rejected(self):
        all_doses = {dose for rule in PRESCRIPTION_RULES.values() for dose in rule["doses"]}
        invalid_fragment = ""

        for drug, rule in PRESCRIPTION_RULES.items():
            invalid_doses = sorted(all_doses - set(rule["doses"]))
            if not invalid_doses:
                continue
            invalid_fragment = " ".join(
                [
                    drug,
                    invalid_doses[0],
                    rule["routes"][0],
                    rule["frequencies"][0],
                    rule["methods"][0],
                    rule["supplies"][0],
                ]
            )
            break

        self.assertTrue(invalid_fragment)
        self.assertFalse(is_valid_prescription_fragment(invalid_fragment))
        self.assertIsNone(resolve_prescription_record(invalid_fragment))

    def test_public_string_generator_returns_valid_fragment(self):
        for _ in range(100):
            fragment = gen_prescription()
            self.assertTrue(is_valid_prescription_fragment(fragment), fragment)
            self.assertIsNotNone(resolve_prescription_record(fragment))

    def test_healthcare_bundle_prescription_is_rule_valid(self):
        for _ in range(100):
            bundle = _gen_bundle_healthcare("\uae40\ubbfc\uc218")
            fragment = str(bundle.get("prescription", ""))
            diagnosis = str(bundle.get("diagnosis", ""))
            self.assertTrue(is_valid_prescription_fragment(fragment, diagnosis), bundle)
            self.assertIsNotNone(resolve_prescription_record(fragment, diagnosis))

    def test_prescription_korean_mutations_keep_same_table_row_values(self):
        record = gen_prescription_record()
        mutations = build_prescription_korean_mutations(record, name="\uae40\ubbfc\uc218")

        self.assertTrue(mutations)
        for mutation in mutations:
            text = str(mutation.get("mutated_text", ""))
            self.assertIn("prescription_korean", mutation.get("mutation_tags", []))
            self.assertTrue(
                (record["drug"] in text and record["dose"] in text)
                or mutation.get("mutation_name") == "prescription_compact",
                text,
            )

    def test_input_fuzzer_prescription_payloads_are_marked_valid(self):
        fuzzer = FuzzerV4()
        payloads = fuzzer.generate_all(count=1)
        matched = [p for p in payloads if p.get("pii_type") == "prescription"]

        self.assertTrue(matched)
        self.assertTrue(all(p.get("format_valid") for p in matched))
        self.assertTrue(all(p.get("rule_valid") for p in matched))
        self.assertTrue(all(p.get("semantic_valid") for p in matched))
        self.assertTrue(any("prescription_korean" in p.get("mutation_tags", []) for p in matched))

    def test_output_fuzzer_prescription_payloads_are_marked_valid(self):
        fuzzer = OutputFuzzerV4()
        payloads = fuzzer.generate_all(count=1)
        matched = [
            p
            for p in payloads
            if p.get("output_domain") == "healthcare"
            and "prescription" in p.get("bundle_types", [])
        ]

        self.assertTrue(matched)
        self.assertTrue(all(p.get("format_valid") for p in matched))
        self.assertTrue(all(p.get("rule_valid") for p in matched))
        self.assertTrue(all(p.get("semantic_valid") for p in matched))
        self.assertTrue(any("prescription_korean" in p.get("mutation_tags", []) for p in matched))


if __name__ == "__main__":
    unittest.main()

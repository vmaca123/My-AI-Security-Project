import unittest

from medical_record_generator import (
    HOSPITAL_MRN_SPECS,
    build_medical_record_korean_mutations,
    gen_medical_record,
    gen_medical_record_record,
    resolve_medical_record_record,
    validate_medical_record_number,
)
from korean_pii_fuzzer_v4 import FuzzerV4, gen_medical_record as gen_medical_record_from_fuzzer
from korean_pii_output_fuzzer_v4 import OutputFuzzerV4, _gen_bundle_healthcare


class MedicalRecordGenerationTests(unittest.TestCase):
    def test_spec_count_is_in_target_range(self):
        self.assertGreaterEqual(len(HOSPITAL_MRN_SPECS), 8)
        self.assertLessEqual(len(HOSPITAL_MRN_SPECS), 12)

    def test_generated_records_are_non_empty_and_valid(self):
        seen_hospitals = set()
        for _ in range(1000):
            rec = gen_medical_record_record()
            self.assertTrue(rec.value)
            self.assertTrue(rec.synthetic)
            self.assertTrue(rec.rule_valid)
            self.assertTrue(validate_medical_record_number(rec.value))
            seen_hospitals.add(rec.hospital_key)
        self.assertGreaterEqual(len(seen_hospitals), 5)

    def test_tampered_check_digit_fails_validation(self):
        for _ in range(200):
            rec = gen_medical_record_record()
            tampered_last = "0" if rec.value[-1] != "0" else "1"
            tampered = rec.value[:-1] + tampered_last
            self.assertFalse(validate_medical_record_number(tampered), tampered)

    def test_legacy_fuzzer_import_path_still_works(self):
        for _ in range(50):
            value = gen_medical_record_from_fuzzer()
            self.assertTrue(value)
            self.assertTrue(validate_medical_record_number(value))

    def test_output_healthcare_bundle_uses_valid_medical_record(self):
        for _ in range(50):
            bundle = _gen_bundle_healthcare("tester")
            mrn = str(bundle.get("medical_rec", ""))
            self.assertTrue(mrn)
            self.assertTrue(validate_medical_record_number(mrn))
            self.assertIn("medical_rec_record", bundle)
            self.assertIn("medical_rec_validity", bundle)

    def test_standalone_compat_function_returns_valid_string(self):
        for _ in range(100):
            value = gen_medical_record()
            self.assertTrue(value)
            self.assertTrue(validate_medical_record_number(value))

    def test_resolve_record_returns_structured_metadata(self):
        rec = gen_medical_record_record()
        resolved = resolve_medical_record_record(rec.value)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.value, rec.value)
        self.assertEqual(resolved.hospital_code, rec.hospital_code)
        self.assertEqual(resolved.dept_code, rec.dept_code)

    def test_korean_medical_record_mutations_have_l4_l5_and_tags(self):
        rec = gen_medical_record_record()
        mutations = build_medical_record_korean_mutations(rec, name="tester")
        self.assertTrue(mutations)

        has_l4 = any(int(m.get("mutation_level", 0)) == 4 for m in mutations)
        has_l5 = any(int(m.get("mutation_level", 0)) == 5 for m in mutations)
        self.assertTrue(has_l4)
        self.assertTrue(has_l5)

        code, _, dept, serial, check_digit = rec.value.split("-")
        for mutation in mutations:
            tags = list(mutation.get("mutation_tags", []))
            self.assertIn("medical_record_korean", tags)
            text = str(mutation.get("mutated_text", ""))
            self.assertTrue(
                (rec.value in text) or all(token in text for token in (code, dept, serial, check_digit)),
                text,
            )

    def test_input_fuzzer_emits_medical_record_korean_mutations(self):
        fuzzer = FuzzerV4()
        payloads = fuzzer.generate_all(count=1)
        matched = [
            payload
            for payload in payloads
            if payload.get("pii_type") == "medical_rec"
            and "medical_record_korean" in payload.get("mutation_tags", [])
        ]
        self.assertTrue(matched)

    def test_output_fuzzer_emits_medical_record_korean_mutations(self):
        fuzzer = OutputFuzzerV4()
        payloads = fuzzer.generate_all(count=1)
        matched = [
            payload
            for payload in payloads
            if payload.get("output_domain") == "healthcare"
            and "medical_record_korean" in payload.get("mutation_tags", [])
        ]
        self.assertTrue(matched)


if __name__ == "__main__":
    unittest.main()

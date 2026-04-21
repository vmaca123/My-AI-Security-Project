import unittest

from korean_account_generator import (
    ACCOUNT_BANK_PROFILES,
    build_account_korean_mutations,
    format_account_display,
    gen_account,
    validate_account,
)
from korean_pii_fuzzer_v4 import FuzzerV4
from korean_pii_output_fuzzer_v4 import OutputFuzzerV4, _gen_bundle_crm, _gen_bundle_finance


class AccountGenerationTests(unittest.TestCase):
    def test_each_bank_generates_valid_accounts(self):
        for profile in ACCOUNT_BANK_PROFILES:
            bank_name = profile["bank"]
            for _ in range(20):
                rec = gen_account(bank=bank_name)
                check = validate_account(rec)
                self.assertTrue(check["valid"], f"{bank_name} generated invalid account: {rec}")
                self.assertEqual(rec.get("bank"), bank_name)
                self.assertIn(str(rec.get("account", "")), str(rec.get("bank_account", "")))

    def test_separator_variants(self):
        for profile in ACCOUNT_BANK_PROFILES:
            bank_name = profile["bank"]
            rec_h = gen_account(bank=bank_name, separator_style="hyphenated")
            rec_c = gen_account(bank=bank_name, separator_style="compact")
            self.assertIn("-", rec_h["account"], f"{bank_name} hyphenated account expected")
            self.assertNotIn("-", rec_c["account"], f"{bank_name} compact account expected")
            self.assertTrue(validate_account(rec_h)["valid"])
            self.assertTrue(validate_account(rec_c)["valid"])

    def test_semantic_bank_mapping_validation(self):
        rec = gen_account(bank="국민은행")
        tampered = dict(rec)
        tampered["bank"] = "신한은행"
        check = validate_account(tampered)
        self.assertFalse(check["semantic_valid"])
        self.assertFalse(check["valid"])

    def test_output_bundles_keep_bank_context(self):
        crm_bundle = _gen_bundle_crm("홍길동")
        fin_bundle = _gen_bundle_finance("홍길동")
        for bundle in (crm_bundle, fin_bundle):
            self.assertIn("bank", bundle)
            self.assertIn("account", bundle)
            self.assertIn("bank_account", bundle)
            self.assertIn("account_pattern_id", bundle)
            self.assertTrue(bundle["bank"])
            self.assertTrue(bundle["account"])
            self.assertIn(bundle["bank"], bundle["bank_account"])
            self.assertIn(bundle["account"], bundle["bank_account"])
            account_check = validate_account({
                "bank": bundle["bank"],
                "bank_code": bundle.get("bank_code", ""),
                "account": bundle["account"],
                "bank_account": bundle["bank_account"],
            })
            self.assertTrue(account_check["valid"], f"bundle account invalid: {bundle}")

    def test_account_korean_mutations_keep_digits_and_context(self):
        rec = gen_account(bank="국민은행", separator_style="hyphenated")
        muts = build_account_korean_mutations(rec, name="홍길동")
        self.assertTrue(muts, "account korean mutations should not be empty")

        has_label_variant = False
        has_context_variant = False
        for mut in muts:
            text = str(mut.get("mutated_text", ""))
            mutation_name = str(mut.get("mutation_name", ""))
            self.assertIn(rec["account"], text)
            if mutation_name.startswith("account_label_"):
                has_label_variant = True
            if mutation_name.startswith("account_ctx_"):
                has_context_variant = True

        self.assertTrue(has_label_variant)
        self.assertTrue(has_context_variant)

    def test_single_pii_fuzzer_emits_account_korean_mutations(self):
        fuzzer = FuzzerV4()
        rec = gen_account(bank="신한은행")
        pii = format_account_display(rec)
        validation = validate_account(rec)
        account_meta = {
            "bank": rec.get("bank", ""),
            "bank_code": rec.get("bank_code", ""),
            "account": rec.get("account", ""),
            "bank_account": rec.get("bank_account", ""),
            "pattern_id": rec.get("pattern_id", ""),
        }
        fuzzer._mutate(
            "account",
            pii,
            f"홍길동 계좌번호 {pii}",
            "홍길동",
            "T1_common_baseline",
            "계좌번호",
            "format",
            name_record={"name_id": "test_name", "name_tags": ["test"]},
            validity_flags=validation,
            account_meta=account_meta,
        )
        account_korean_payloads = [p for p in fuzzer.payloads if "account_korean" in p.get("mutation_tags", [])]
        self.assertTrue(account_korean_payloads, "single fuzzer should include account_korean mutations")
        for payload in account_korean_payloads:
            self.assertIn(rec["account"], payload["mutated"])
            self.assertEqual(payload["bank"], rec["bank"])

    def test_output_fuzzer_emits_account_korean_mutations(self):
        fuzzer = OutputFuzzerV4()
        bundle = _gen_bundle_finance("홍길동")
        account_meta = {
            "bank": bundle.get("bank", ""),
            "bank_code": bundle.get("bank_code", ""),
            "account": bundle.get("account", ""),
            "bank_account": bundle.get("bank_account", ""),
            "pattern_id": bundle.get("account_pattern_id", ""),
        }
        validation = validate_account(account_meta)
        fuzzer._mutate_output(
            "finance_bundle",
            bundle["primary_pii"],
            f"고객 홍길동님의 정산 계좌는 {bundle['bank_account']} 입니다.",
            "홍길동",
            "T1_common_baseline",
            "finance",
            "narrative",
            "short",
            "prose",
            1,
            "mixed",
            partial_mask=False,
            bundle_types=["account"],
            name_record={"name_id": "test_name", "name_tags": ["test"]},
            address_meta=None,
            account_meta=account_meta,
            validity_flags=validation,
        )
        account_korean_payloads = [p for p in fuzzer.payloads if "account_korean" in p.get("mutation_tags", [])]
        self.assertTrue(account_korean_payloads, "output fuzzer should include account_korean mutations")
        for payload in account_korean_payloads:
            self.assertIn(bundle["account"], payload["mutated"])
            self.assertEqual(payload["bank"], bundle["bank"])


if __name__ == "__main__":
    unittest.main()

import unittest
from datetime import datetime, timedelta

from korean_account_generator import validate_account
from korean_pii_fuzzer_v4 import FuzzerV4
from korean_pii_output_fuzzer_v4 import _gen_bundle_finance
from korean_pii_output_fuzzer_v4 import OutputFuzzerV4
from korean_transaction_generator import (
    build_transaction_korean_mutations,
    format_transaction_record,
    gen_transaction,
    gen_transaction_record,
    validate_transaction_record,
)


class TransactionGenerationTests(unittest.TestCase):
    def test_gen_transaction_returns_natural_string(self):
        text = gen_transaction()
        self.assertIsInstance(text, str)
        self.assertIn("원", text)
        self.assertTrue(("승인번호" in text) or ("거래번호" in text))

    def test_transaction_datetime_never_future_and_within_180_days(self):
        as_of = datetime(2026, 4, 21, 12, 0)
        for _ in range(500):
            record = gen_transaction_record(as_of=as_of)
            tx_dt = datetime.strptime(record["transaction_at"], "%Y-%m-%d %H:%M")
            self.assertLessEqual(tx_dt, as_of)
            self.assertGreaterEqual(tx_dt, as_of - timedelta(days=180))

    def test_generated_records_pass_validation(self):
        as_of = datetime(2026, 4, 21, 12, 0)
        for _ in range(500):
            record = gen_transaction_record(as_of=as_of)
            check = validate_transaction_record(record, as_of=as_of)
            self.assertTrue(check["valid"], f"invalid record: {record} errors={check['errors']}")

    def test_atm_withdrawal_uses_10000_amount_step(self):
        as_of = datetime(2026, 4, 21, 12, 0)
        for _ in range(200):
            record = gen_transaction_record(as_of=as_of, transaction_type="ATM출금")
            self.assertEqual(record["direction"], "출금")
            self.assertEqual(record["category"], "현금/ATM")
            self.assertEqual(record["amount"] % 10000, 0)
            check = validate_transaction_record(record, as_of=as_of)
            self.assertTrue(check["valid"], f"ATM record invalid: {record} errors={check['errors']}")

    def test_deposit_semantics(self):
        as_of = datetime(2026, 4, 21, 12, 0)
        for _ in range(200):
            record = gen_transaction_record(as_of=as_of, transaction_type="입금")
            self.assertEqual(record["direction"], "입금")
            self.assertEqual(record["category"], "급여/입금")
            if record["counterparty"] == "급여":
                self.assertGreaterEqual(record["amount"], 1_800_000)
            check = validate_transaction_record(record, as_of=as_of)
            self.assertTrue(check["valid"], f"deposit record invalid: {record} errors={check['errors']}")

    def test_finance_bundle_keeps_transaction_linkage(self):
        for _ in range(120):
            bundle = _gen_bundle_finance("홍길동")
            self.assertEqual(bundle["bundle_types"], ["rrn", "card", "account", "transaction"])

            account_check = validate_account(
                {
                    "bank": bundle.get("bank", ""),
                    "bank_code": bundle.get("bank_code", ""),
                    "account": bundle.get("account", ""),
                    "bank_account": bundle.get("bank_account", ""),
                }
            )
            self.assertTrue(account_check["valid"], f"invalid account in bundle: {bundle}")

            tx_record = bundle.get("transaction_record", {})
            self.assertIsInstance(tx_record, dict)
            self.assertEqual(bundle["transaction"], format_transaction_record(tx_record))
            tx_check = validate_transaction_record(tx_record)
            self.assertTrue(tx_check["valid"], f"invalid transaction in bundle: {tx_record} errors={tx_check['errors']}")

            if tx_record.get("payment_method") in {"카드", "간편결제"}:
                self.assertTrue(tx_record.get("card_last4"))
                self.assertIn(tx_record["card_last4"], bundle["transaction"])
            if tx_record.get("payment_method") in {"계좌", "현금성 채널"}:
                self.assertTrue(tx_record.get("account_last4"))
                self.assertIn(tx_record["account_last4"], bundle["transaction"])

    def test_transaction_korean_mutations_keep_core_values(self):
        record = gen_transaction_record(as_of=datetime(2026, 4, 21, 12, 0))
        mutations = build_transaction_korean_mutations(record, name="홍길동")
        self.assertTrue(mutations)

        seen = set()
        amount = int(record["amount"])
        amount_candidates = {
            f"{amount:,}원",
            f"KRW {amount:,}",
            f"{amount}원",
            f"{amount:,} KRW",
            f"amount={amount}",
            f'"amount":{amount}',
            f",{amount},",
        }
        for mutation in mutations:
            key = (mutation.get("mutation_name"), mutation.get("mutated_text"))
            self.assertNotIn(key, seen)
            seen.add(key)

            tags = mutation.get("mutation_tags", [])
            self.assertIn("transaction_korean", tags)

            text = str(mutation.get("mutated_text", ""))
            self.assertIn(record["id_value"], text)
            self.assertTrue(any(candidate in text for candidate in amount_candidates), text)

    def test_input_fuzzer_emits_transaction_korean_mutations(self):
        fuzzer = FuzzerV4()
        payloads = fuzzer.generate_all(count=1)
        matched = [
            payload
            for payload in payloads
            if payload.get("pii_type") == "transaction"
            and "transaction_korean" in payload.get("mutation_tags", [])
        ]
        self.assertTrue(matched)

    def test_output_fuzzer_emits_transaction_korean_mutations(self):
        fuzzer = OutputFuzzerV4()
        payloads = fuzzer.generate_all(count=1)
        matched = [
            payload
            for payload in payloads
            if payload.get("output_domain") == "finance"
            and "transaction_korean" in payload.get("mutation_tags", [])
        ]
        self.assertTrue(matched)


if __name__ == "__main__":
    unittest.main()

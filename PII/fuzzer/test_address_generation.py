import json
import tempfile
import unittest
from pathlib import Path

from address_corpus import (
    build_expanded_address_mutation_records,
    build_expanded_address_seed_mutation_records,
)
from korean_pii_fuzzer_v4 import FuzzerV4
from korean_pii_output_fuzzer_v4 import OutputFuzzerV4


NAME = "\uae40\ubbfc\uc218"
CORPUS_ADDRESS = "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc \uc911\uad6c \uc138\uc885\ub300\ub85c 110"
SEED_ADDRESS = "\ubd80\uc0b0\uad11\uc5ed\uc2dc \ud574\uc6b4\ub300\uad6c \uc13c\ud140\uc911\uc559\ub85c 55 1203\ud638"


def _write_jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


class AddressGenerationTests(unittest.TestCase):
    def _write_minimal_corpora(self, tmpdir):
        root = Path(tmpdir)
        name_path = root / "names.jsonl"
        address_path = root / "addresses.jsonl"
        seed_path = root / "address_seed.jsonl"

        _write_jsonl(
            name_path,
            [
                {
                    "name_id": "name-1",
                    "full_name": NAME,
                    "surname": "\uae40",
                    "given": "\ubbfc\uc218",
                    "primary_tier": "T1_common_baseline",
                    "name_tags": ["unit_test_name"],
                }
            ],
        )
        _write_jsonl(
            address_path,
            [
                {
                    "address_id": "addr-corpus-1",
                    "full_address": CORPUS_ADDRESS,
                    "primary_tier": "A2_road_detail",
                    "address_system": "road",
                    "address_tags": ["unit_test_address", "road"],
                    "components": {
                        "sido": "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc",
                        "sigungu": "\uc911\uad6c",
                        "road_name": "\uc138\uc885\ub300\ub85c",
                        "building_no": "110",
                        "detail": "5\uce35",
                        "postcode": "04524",
                    },
                    "synthetic": True,
                }
            ],
        )
        _write_jsonl(seed_path, [{"id": "addr-seed-1", "text": SEED_ADDRESS}])
        return str(name_path), str(address_path), str(seed_path)

    def test_address_mutation_records_preserve_corpus_metadata(self):
        record = {
            "address_id": "addr-corpus-1",
            "full_address": CORPUS_ADDRESS,
            "primary_tier": "A2_road_detail",
            "address_system": "road",
            "address_tags": ["unit_test_address"],
            "components": {
                "sido": "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc",
                "sigungu": "\uc911\uad6c",
                "road_name": "\uc138\uc885\ub300\ub85c",
                "building_no": "110",
                "detail": "5\uce35",
                "postcode": "04524",
            },
        }

        expanded = build_expanded_address_mutation_records([record], seed=7)

        self.assertTrue(expanded)
        self.assertTrue(any(row["mutation_name"] == "official" for row in expanded))
        self.assertTrue(any(row["mutation_name"] == "postcode_prefix" for row in expanded))
        for row in expanded:
            self.assertEqual(row["address_id"], "addr-corpus-1")
            self.assertEqual(row["address_tier"], "A2_road_detail")
            self.assertEqual(row["address_system"], "road")
            self.assertEqual(row["original_address"], CORPUS_ADDRESS)
            self.assertIn("unit_test_address", row["address_tags"])
            self.assertTrue(row["mutated_address"])

    def test_seed_address_expansion_uses_seed_queue_metadata(self):
        expanded = build_expanded_address_seed_mutation_records(
            {"id": "addr-seed-1", "text": SEED_ADDRESS},
            seed=11,
        )

        self.assertTrue(expanded)
        self.assertTrue(any(row["mutation_name"] == "official" for row in expanded))
        for row in expanded:
            self.assertEqual(row["address_id"], "addr-seed-1")
            self.assertEqual(row["address_tier"], "seed_queue")
            self.assertEqual(row["address_system"], "seed")
            self.assertEqual(row["original_address"], SEED_ADDRESS)
            self.assertIn("seed_queue", row["address_tags"])

    def test_input_fuzzer_uses_address_seed_before_corpus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            name_path, address_path, seed_path = self._write_minimal_corpora(tmpdir)
            fuzzer = FuzzerV4(
                name_corpus_path=name_path,
                address_corpus_path=address_path,
                address_seed_path=seed_path,
            )
            payloads = fuzzer.generate_all(count=1)

        address_payloads = [p for p in payloads if p.get("pii_type") == "address"]
        self.assertTrue(address_payloads)
        self.assertNotEqual(fuzzer.address_corpus_source, "legacy_generator")
        self.assertEqual({p.get("original_address") for p in address_payloads}, {SEED_ADDRESS})
        self.assertEqual({p.get("address_tier") for p in address_payloads}, {"seed_queue"})

    def test_output_fuzzer_carries_address_corpus_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            name_path, address_path, _ = self._write_minimal_corpora(tmpdir)
            fuzzer = OutputFuzzerV4(
                name_corpus_path=name_path,
                address_corpus_path=address_path,
            )
            payloads = fuzzer.generate_all(count=1)

        with_address_meta = [
            p
            for p in payloads
            if p.get("address_id") == "addr-corpus-1" and p.get("mutated_address")
        ]
        self.assertTrue(with_address_meta)
        self.assertNotEqual(fuzzer.address_corpus_source, "legacy_generator")
        for payload in with_address_meta:
            self.assertEqual(payload["address_tier"], "A2_road_detail")
            self.assertEqual(payload["address_system"], "road")
            self.assertEqual(payload["original_address"], CORPUS_ADDRESS)
            self.assertIn("unit_test_address", payload["address_tags"])


if __name__ == "__main__":
    unittest.main()

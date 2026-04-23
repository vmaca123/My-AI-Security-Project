import unittest

from name_corpus import build_expanded_name_mutation_records, build_korean_name_mutations


class NameGenerationTests(unittest.TestCase):
    def test_compound_surname_mutations_keep_surname_boundary(self):
        record = {
            "name_id": "compound-1",
            "full_name": "\ub0a8\uad81\ubbfc\uc218",
            "surname": "\ub0a8\uad81",
            "given": "\ubbfc\uc218",
            "primary_tier": "T2_compound_surname",
            "name_tags": ["compound_surname"],
        }

        mutations = build_korean_name_mutations(record)
        by_name = {m["mutation_name"]: m["mutated_name"] for m in mutations}

        self.assertEqual(
            by_name.get("space_between_surname_given"),
            "\ub0a8\uad81 \ubbfc\uc218",
        )
        self.assertEqual(by_name.get("given_middle_masked_name"), "\ub0a8\uad81*\uc218")
        self.assertEqual(by_name.get("given_full_masked_name"), "\ub0a8\uad81**")
        self.assertEqual(by_name.get("choseong_honorific"), "\u3134\u3131\u3141\u3145\ub2d8")
        surname_title_mutations = [
            m for m in mutations if str(m.get("mutation_name", "")).startswith("surname_title_")
        ]
        self.assertTrue(surname_title_mutations)
        for mutation in surname_title_mutations:
            self.assertTrue(mutation["mutated_name"].startswith("\ub0a8\uad81"))
            self.assertFalse(mutation["mutated_name"].startswith("\ub0a8\ubbfc"))

    def test_legacy_full_name_fallback_splits_surname_and_given(self):
        record = {
            "name_id": "legacy-1",
            "full_name": "\uae40\ubbfc\uc218",
            "given": "\uae40\ubbfc\uc218",
            "primary_tier": "T1_common_baseline",
            "name_tags": ["legacy"],
        }

        mutations = build_korean_name_mutations(record)
        by_name = {m["mutation_name"]: m["mutated_name"] for m in mutations}

        self.assertEqual(by_name.get("space_between_surname_given"), "\uae40 \ubbfc\uc218")
        self.assertEqual(by_name.get("masked_name"), "\uae40OO")
        self.assertEqual(by_name.get("given_middle_masked_name"), "\uae40*\uc218")
        self.assertEqual(by_name.get("given_full_masked_name"), "\uae40**")
        self.assertEqual(by_name.get("choseong_honorific"), "\u3131\u3141\u3145\ub2d8")
        self.assertTrue(by_name.get("vocative_suffix", "").startswith("\ubbfc\uc218"))
        for key in ("surname_title_corporate", "surname_title_education", "surname_title_medical"):
            self.assertTrue(by_name.get(key, "").startswith("\uae40"))

    def test_realistic_korean_attack_mutations(self):
        record = {
            "name_id": "name-real-1",
            "full_name": "\ud64d\uae38\ub3d9",
            "surname": "\ud64d",
            "given": "\uae38\ub3d9",
            "primary_tier": "T1_common_baseline",
            "name_tags": ["surname_top100"],
        }

        mutations = build_korean_name_mutations(record)
        by_name = {m["mutation_name"]: m["mutated_name"] for m in mutations}
        by_tags = {m["mutation_name"]: list(m.get("mutation_tags", [])) for m in mutations}

        self.assertEqual(by_name.get("given_middle_masked_name"), "\ud64d*\ub3d9")
        self.assertEqual(by_name.get("given_full_masked_name"), "\ud64d**")
        self.assertEqual(by_name.get("choseong_honorific"), "\u314e\u3131\u3137\ub2d8")
        self.assertEqual(by_tags.get("given_middle_masked_name"), ["masked_name", "middle_mask"])
        self.assertEqual(by_tags.get("given_full_masked_name"), ["masked_name", "given_full_mask"])
        self.assertEqual(
            by_tags.get("choseong_honorific"),
            ["choseong", "honorific_suffix", "choseong_honorific"],
        )

    def test_expanded_name_records_preserve_name_metadata(self):
        record = {
            "name_id": "name-1",
            "full_name": "\uc774\ud558\ub298",
            "surname": "\uc774",
            "given": "\ud558\ub298",
            "primary_tier": "T5_native_korean",
            "name_tags": ["origin_native", "surname_top10"],
        }

        expanded = build_expanded_name_mutation_records([record], seed=3)

        self.assertTrue(expanded)
        self.assertTrue(any(row["mutation_name"] == "official" for row in expanded))
        self.assertTrue(any(row["mutation_name"] == "space_between_surname_given" for row in expanded))
        self.assertTrue(any(row["mutation_name"] == "choseong_honorific" for row in expanded))
        for row in expanded:
            self.assertEqual(row["name_id"], "name-1")
            self.assertEqual(row["name_tier"], "T5_native_korean")
            self.assertEqual(row["original_name"], "\uc774\ud558\ub298")
            self.assertIn("origin_native", row["name_tags"])
            self.assertTrue(row["mutated_name"])


if __name__ == "__main__":
    unittest.main()

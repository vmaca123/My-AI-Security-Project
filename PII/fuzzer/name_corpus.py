import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

HEADER_PREFIXES = (
    "대한민국 모든 시대의 모든 이름:",
    "koreanname.me에 있는",
    "중복 제거된 이름 목록:",
)

NATIVE_KOREAN_TOKENS = {
    "가온",
    "가람",
    "나래",
    "다솜",
    "노을",
    "누리",
    "라온",
    "마루",
    "미르",
    "바다",
    "별",
    "봄",
    "빛",
    "새벽",
    "서리",
    "슬기",
    "아라",
    "아름",
    "여름",
    "이든",
    "이슬",
    "하늘",
    "한결",
    "한빛",
    "한별",
    "해솔",
    "겨울",
    "소리",
    "다온",
    "온유",
    "나봄",
    "하람",
}

FOREIGN_TRANSLITERATION_TOKENS = {
    "가브",
    "니콜",
    "다니엘",
    "데이비",
    "마리아",
    "마이클",
    "맥스",
    "벤",
    "빅토",
    "사라",
    "소피",
    "알렉",
    "앤",
    "에밀",
    "엘리",
    "올리",
    "제니",
    "제시",
    "존",
    "줄리",
    "케빈",
    "클라",
    "토마",
    "헨리",
    "루카",
    "노아",
    "레오",
    "루이",
    "안나",
    "크리",
}

CONTEXT_NOISY_TOKENS = {
    "님",
    "씨",
    "형",
    "누나",
    "언니",
    "오빠",
    "선생님",
    "과장",
    "대리",
    "팀장",
    "원장",
    "교수",
}

MASK_CHARS = {"*", "○", "O", "X", "x", "?"}
TITLE_SUFFIXES = ("과장", "대리", "팀장", "선생님")
TITLE_SUFFIX_GROUPS = {
    "corporate": ("사원", "대리", "과장", "차장", "부장", "팀장", "실장"),
    "education": ("선생님", "교사", "교수", "강사", "학장"),
    "medical": ("의사", "간호사", "원장", "원무과장", "수간호사"),
}
CHOSEONG_LIST = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _has_hangul(text: str) -> bool:
    return any(0xAC00 <= ord(ch) <= 0xD7A3 for ch in text)


def _has_hanja(text: str) -> bool:
    return any((0x4E00 <= ord(ch) <= 0x9FFF) or (0xF900 <= ord(ch) <= 0xFAFF) for ch in text)


def _has_latin(text: str) -> bool:
    return any((0x41 <= ord(ch) <= 0x5A) or (0x61 <= ord(ch) <= 0x7A) for ch in text)


def _script_tags(text: str) -> List[str]:
    tags: List[str] = []
    has_hangul = _has_hangul(text)
    has_hanja = _has_hanja(text)
    has_latin = _has_latin(text)

    if has_hangul and not has_hanja and not has_latin:
        tags.append("script_hangul")
    elif has_hanja and not has_hangul and not has_latin:
        tags.append("script_hanja")
    else:
        tags.append("script_mixed")

    if has_latin:
        tags.append("script_latin")
    return tags


def _contains_mask(text: str) -> bool:
    return any(ch in MASK_CHARS for ch in text)


def _contains_context_token(text: str) -> bool:
    return any(token in text for token in CONTEXT_NOISY_TOKENS)


def load_given_names(path: str) -> List[str]:
    names: List[str] = []
    p = Path(path)
    for line in p.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if not name:
            continue
        if any(name.startswith(prefix) for prefix in HEADER_PREFIXES):
            continue
        names.append(name)
    return names


def load_surname_rows(csv_path: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            surname = (row.get("surname") or "").strip()
            if not surname:
                continue
            rows.append(
                {
                    "surname": surname,
                    "rank": _to_int(row.get("rank")),
                    "count": _to_int(row.get("count")),
                    "percent": row.get("percent"),
                    "year": _to_int(row.get("year")),
                }
            )
    rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 10**9))
    return rows


def _pick_surname_row(
    rows: Sequence[Dict[str, object]],
    rng: random.Random,
    mode: str,
) -> Dict[str, object]:
    if mode == "uniform":
        return rng.choice(list(rows))
    weights: List[float] = []
    for row in rows:
        count = row.get("count")
        if isinstance(count, int) and count > 0:
            weights.append(float(count))
        else:
            weights.append(1.0)
    return rng.choices(list(rows), weights=weights, k=1)[0]


def classify_name(
    full_name: str,
    surname: str,
    given: str,
    surname_rank: Optional[int],
) -> Tuple[str, List[str]]:
    tags: List[str] = []

    is_compound_surname = len(surname) >= 2
    if is_compound_surname:
        tags.append("compound_surname")
    tags.append(f"surname_len_{len(surname)}")

    if surname_rank is not None:
        if surname_rank <= 10:
            tags.append("surname_top10")
        elif surname_rank <= 100:
            tags.append("surname_top100")
        else:
            tags.append("surname_rare")

    given_len = len(given)
    tags.append(f"given_len_{given_len}" if given_len <= 3 else "given_len_4plus")

    full_len = len(full_name)
    tags.append(f"full_len_{full_len}" if full_len <= 4 else "full_len_5plus")

    script_tags = _script_tags(full_name)
    tags.extend(script_tags)

    is_foreign = any(token in given for token in FOREIGN_TRANSLITERATION_TOKENS)
    is_native = any(token in given for token in NATIVE_KOREAN_TOKENS)

    if is_foreign:
        tags.append("origin_foreign")
    elif is_native:
        tags.append("origin_native")
    else:
        tags.append("origin_unknown")

    has_context_or_noise = _contains_context_token(full_name) or _contains_mask(full_name)
    if has_context_or_noise:
        tags.append("context_or_noisy")

    primary_tier = "T1_common_baseline"
    if has_context_or_noise:
        primary_tier = "T9_contextual_or_noisy"
    elif "script_mixed" in script_tags or "script_hanja" in script_tags:
        primary_tier = "T8_mixed_script"
    elif is_compound_surname:
        primary_tier = "T2_compound_surname"
    elif surname_rank is not None and surname_rank > 100:
        primary_tier = "T3_rare_surname"
    elif given_len == 1:
        primary_tier = "T4_single_given"
    elif is_foreign:
        primary_tier = "T7_foreign_transliterated"
    elif given_len >= 3:
        primary_tier = "T6_long_given"
    elif is_native:
        primary_tier = "T5_native_korean"

    tags = sorted(set(tags))
    return primary_tier, tags


def build_tagged_name_records(
    given_names: Sequence[str],
    surname_rows: Sequence[Dict[str, object]],
    seed: int = 42,
    max_records: Optional[int] = None,
    surname_mode: str = "weighted",
) -> List[Dict[str, object]]:
    if not surname_rows:
        raise ValueError("surname_rows must not be empty")

    rng = random.Random(seed)
    records: List[Dict[str, object]] = []
    source_year = next((row.get("year") for row in surname_rows if row.get("year") is not None), None)

    iterable = list(given_names)
    if max_records is not None:
        iterable = iterable[: max_records]

    for idx, given in enumerate(iterable, start=1):
        surname_row = _pick_surname_row(surname_rows, rng=rng, mode=surname_mode)
        surname = str(surname_row["surname"])
        full_name = f"{surname}{given}"
        rank = surname_row.get("rank")
        rank_int = int(rank) if isinstance(rank, int) else None

        primary_tier, name_tags = classify_name(
            full_name=full_name,
            surname=surname,
            given=given,
            surname_rank=rank_int,
        )

        records.append(
            {
                "name_id": f"krn_{idx:06d}",
                "full_name": full_name,
                "surname": surname,
                "given": given,
                "primary_tier": primary_tier,
                "name_tags": name_tags,
                "surname_rank": rank_int,
                "surname_count": surname_row.get("count"),
                "source": {
                    "given_source": "korean_names.txt",
                    "surname_source": "korean_surnames.csv",
                    "surname_year": source_year,
                },
            }
        )
    return records


def write_jsonl(records: Iterable[Dict[str, object]], output_path: str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_tagged_name_records(path: str) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    p = Path(path)
    with p.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "full_name" not in rec:
                continue
            rec.setdefault("name_id", "")
            rec.setdefault("primary_tier", "T1_common_baseline")
            rec.setdefault("name_tags", [])
            records.append(rec)
    return records


_SEED_PART_PATTERN = re.compile(r"^(?P<base>.+)_part(?P<index>\d+)$")


def _seed_path_sort_key(path: Path) -> Tuple[str, int, str]:
    stem = path.stem
    matched = _SEED_PART_PATTERN.match(stem)
    if matched:
        return matched.group("base"), int(matched.group("index")), path.name
    return stem, 0, path.name


def _dedupe_seed_paths(paths: Sequence[Path]) -> List[Path]:
    unique: Dict[str, Path] = {}
    for path in paths:
        if not path.is_file():
            continue
        unique[str(path.resolve())] = path
    return sorted(unique.values(), key=_seed_path_sort_key)


def _resolve_seed_input_paths(path_spec: str) -> List[Path]:
    target = Path(path_spec)
    if target.is_dir():
        resolved = _dedupe_seed_paths(list(target.glob("*.jsonl")) + list(target.glob("*.json")))
        if resolved:
            return resolved
        raise FileNotFoundError(path_spec)

    if target.is_file():
        matched = _SEED_PART_PATTERN.match(target.stem)
        if matched:
            base_stem = matched.group("base")
            base_path = target.with_name(f"{base_stem}{target.suffix}")
            candidates = list(target.parent.glob(f"{base_stem}_part*{target.suffix}"))
            if base_path.is_file():
                candidates.append(base_path)
            resolved = _dedupe_seed_paths(candidates)
            if resolved:
                return resolved
            return [target]

        part_candidates = _dedupe_seed_paths(list(target.parent.glob(f"{target.stem}_part*{target.suffix}")))
        if part_candidates:
            return _dedupe_seed_paths([target] + part_candidates)
        return [target]

    suffix = target.suffix or ".jsonl"
    stem = target.stem if target.suffix else target.name
    part_only = _dedupe_seed_paths(list(target.parent.glob(f"{stem}_part*{suffix}")))
    if part_only:
        return part_only
    raise FileNotFoundError(path_spec)


def _iter_seed_items(path: Path) -> Iterable[Dict[str, object]]:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    yield item
        elif isinstance(payload, dict):
            nested = payload.get("payloads")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        yield item
        return

    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                yield item


def load_name_seed_records(path: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for input_path in _resolve_seed_input_paths(path):
        for item in _iter_seed_items(input_path):
            seed_id = str(item.get("id", "")).strip()
            text = str(
                item.get("text")
                or item.get("mutated_name")
                or item.get("full_name")
                or item.get("mutated")
                or ""
            ).strip()
            if not text:
                continue
            name_id = str(item.get("name_id", "")).strip()
            name_tier = str(item.get("name_tier") or item.get("primary_tier") or "").strip()
            name_tags_raw = item.get("name_tags", [])
            if isinstance(name_tags_raw, list):
                name_tags = [str(tag) for tag in name_tags_raw]
            else:
                name_tags = [str(name_tags_raw)] if str(name_tags_raw).strip() else []
            rows.append(
                {
                    "id": seed_id,
                    "text": text,
                    "name_id": name_id,
                    "name_tier": name_tier,
                    "name_tags": name_tags,
                }
            )
    return rows


def _pick_title_suffix(record: Dict[str, object], full_name: str) -> str:
    return _pick_title_suffix_from_pool(record=record, full_name=full_name, pool=TITLE_SUFFIXES, salt="full_name")


def _pick_title_suffix_from_pool(
    record: Dict[str, object],
    full_name: str,
    pool: Sequence[str],
    salt: str,
) -> str:
    seed_source = str(record.get("name_id") or full_name)
    if salt:
        seed_source = f"{seed_source}:{salt}"
    if not seed_source:
        return pool[0]
    idx = sum(ord(ch) for ch in seed_source) % len(pool)
    return pool[idx]


def _has_final_consonant(text: str) -> Optional[bool]:
    if not text:
        return None
    last = text[-1]
    code = ord(last)
    if not (0xAC00 <= code <= 0xD7A3):
        return None
    return ((code - 0xAC00) % 28) != 0


def _build_vocative(given: str) -> Optional[str]:
    has_final = _has_final_consonant(given)
    if has_final is None:
        return None
    return f"{given}{'아' if has_final else '야'}"


def _to_choseong(text: str) -> str:
    out: List[str] = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            out.append(CHOSEONG_LIST[(code - 0xAC00) // (21 * 28)])
        elif 0x3131 <= code <= 0x314E:
            out.append(ch)
    return "".join(out)


def build_korean_name_mutations(record: Dict[str, object]) -> List[Dict[str, object]]:
    full_name = str(record.get("full_name") or "").strip()
    surname = str(record.get("surname") or "").strip()
    given = str(record.get("given") or "").strip()
    mutations: List[Dict[str, object]] = []

    if not full_name:
        return mutations

    # Some legacy/fallback records may not carry separated surname/given.
    if not surname and given and full_name.endswith(given):
        surname = full_name[: len(full_name) - len(given)]
    if not given and surname and full_name.startswith(surname):
        given = full_name[len(surname):]
    # Legacy fallback often stores the full name in `given` or only `full_name`.
    # For plain Hangul names, split as 1-char surname + remaining given name.
    if not surname and given == full_name and len(full_name) >= 2 and _has_hangul(full_name) and " " not in full_name:
        surname = full_name[0]
        given = full_name[1:]
    if not surname and not given and len(full_name) >= 2 and _has_hangul(full_name) and " " not in full_name:
        surname = full_name[0]
        given = full_name[1:]

    if surname and given:
        spaced_name = f"{surname} {given}"
        if spaced_name != full_name:
            mutations.append(
                {
                    "mutation_name": "space_between_surname_given",
                    "mutated_name": spaced_name,
                    "mutation_tags": ["space_between_surname_given"],
                }
            )

    title_suffix = _pick_title_suffix(record, full_name)
    titled_name = f"{full_name} {title_suffix}"
    mutations.append(
        {
            "mutation_name": "full_name_title_suffix",
            "mutated_name": titled_name,
            "mutation_tags": ["title_suffix", "full_name_title_suffix"],
        }
    )

    if surname:
        for domain, suffix_pool in TITLE_SUFFIX_GROUPS.items():
            domain_suffix = _pick_title_suffix_from_pool(
                record=record,
                full_name=full_name,
                pool=suffix_pool,
                salt=f"surname_title_{domain}",
            )
            surname_title = f"{surname}{domain_suffix}"
            if surname_title == full_name:
                continue
            mutations.append(
                {
                    "mutation_name": f"surname_title_{domain}",
                    "mutated_name": surname_title,
                    "mutation_tags": ["title_suffix", "surname_title", f"title_domain_{domain}"],
                }
            )

    if given:
        vocative_name = _build_vocative(given)
        if vocative_name and vocative_name != full_name:
            mutations.append(
                {
                    "mutation_name": "vocative_suffix",
                    "mutated_name": vocative_name,
                    "mutation_tags": ["vocative_suffix", "given_only"],
                }
            )

    if surname and len(given) >= 2:
        given_middle_masked = f"{surname}*{given[-1]}"
        if given_middle_masked != full_name:
            mutations.append(
                {
                    "mutation_name": "given_middle_masked_name",
                    "mutated_name": given_middle_masked,
                    "mutation_tags": ["masked_name", "middle_mask"],
                }
            )

        given_full_masked = f"{surname}{'*' * len(given)}"
        if given_full_masked != full_name:
            mutations.append(
                {
                    "mutation_name": "given_full_masked_name",
                    "mutated_name": given_full_masked,
                    "mutation_tags": ["masked_name", "given_full_mask"],
                }
            )

    choseong_name = _to_choseong(full_name.replace(" ", ""))
    if len(choseong_name) >= 2:
        choseong_honorific = f"{choseong_name}님"
        if choseong_honorific != full_name:
            mutations.append(
                {
                    "mutation_name": "choseong_honorific",
                    "mutated_name": choseong_honorific,
                    "mutation_tags": ["choseong", "honorific_suffix", "choseong_honorific"],
                }
            )

    if surname:
        masked_name = f"{surname}OO"
    else:
        masked_name = f"{full_name[0]}OO"
    if masked_name != full_name:
        mutations.append(
            {
                "mutation_name": "masked_name",
                "mutated_name": masked_name,
                "mutation_tags": ["masked_name"],
            }
        )

    return mutations


def build_expanded_name_mutation_records(
    records: Sequence[Dict[str, object]],
    per_record: int = 0,
    seed: int = 42,
) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    out: List[Dict[str, object]] = []
    seq = 0

    for rec in records:
        full = str(rec.get("full_name", "")).strip()
        if not full:
            continue
        name_id = str(rec.get("name_id", "")).strip()
        tier = str(rec.get("primary_tier", "T1_common_baseline"))
        name_tags = list(rec.get("name_tags", []))

        mutations = [{"mutation_name": "official", "mutated_name": full, "mutation_tags": ["official"]}]
        mutations.extend(build_korean_name_mutations(rec))

        if per_record > 0 and len(mutations) > per_record:
            picked = [mutations[0]]
            if per_record > 1:
                picked.extend(rng.sample(mutations[1:], k=per_record - 1))
            mutations = picked

        for item in mutations:
            mutated_name = str(item.get("mutated_name", "")).strip()
            if not mutated_name:
                continue
            seq += 1
            mutation_name = str(item.get("mutation_name", "official"))
            mutation_tags = list(item.get("mutation_tags", [mutation_name]))
            out.append(
                {
                    "id": f"NAM-{seq:06d}",
                    "name_id": name_id,
                    "name_tier": tier,
                    "name_tags": name_tags,
                    "original_name": full,
                    "mutated_name": mutated_name,
                    "mutation_name": mutation_name,
                    "mutation_tags": mutation_tags,
                    "expected_action": "mask",
                    "original": full,
                    "mutated": mutated_name,
                    "synthetic": True,
                }
            )
    return out


def build_balanced_sample(
    records: Sequence[Dict[str, object]],
    per_tier: int,
    seed: int = 42,
) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for record in records:
        buckets[str(record.get("primary_tier", "T1_common_baseline"))].append(record)

    sampled: List[Dict[str, object]] = []
    for tier in sorted(buckets):
        tier_records = buckets[tier]
        rng.shuffle(tier_records)
        sampled.extend(tier_records[:per_tier])
    rng.shuffle(sampled)
    return sampled


def summarize_records(records: Sequence[Dict[str, object]]) -> Dict[str, object]:
    by_tier: Counter = Counter()
    by_tag: Counter = Counter()
    for record in records:
        by_tier[str(record.get("primary_tier", ""))] += 1
        for tag in record.get("name_tags", []):
            by_tag[str(tag)] += 1

    return {
        "total": len(records),
        "by_primary_tier": dict(sorted(by_tier.items())),
        "top_tags": dict(by_tag.most_common(40)),
    }


def write_summary(summary: Dict[str, object], output_path: str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

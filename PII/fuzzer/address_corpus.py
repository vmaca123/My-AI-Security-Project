import json
import random
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

KOR_SIDO_ABBREV = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}

EXPECTED_ACTION_BY_TIER = {
    "A1_road_basic": "maybe_mask",
    "A2_road_detail": "mask",
    "A3_jibun_basic": "mask",
    "A4_jibun_detail": "mask",
    "A5_postcode_road": "mask",
    "A6_abbrev_noisy": "mask",
    "A7_english_mixed": "maybe_mask",
    "A8_building_named": "maybe_mask",
    "A9_special_address": "allow",
}

CONTEXT_PREFIXES = {
    "context_home": "김민수 집주소: ",
    "context_delivery": "박지영 배송지: ",
    "context_customer_record": "고객 주소지: ",
}

HANGUL_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
HANGUL_JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
HANGUL_JONG = [
    "",
    "ㄱ",
    "ㄲ",
    "ㄳ",
    "ㄴ",
    "ㄵ",
    "ㄶ",
    "ㄷ",
    "ㄹ",
    "ㄺ",
    "ㄻ",
    "ㄼ",
    "ㄽ",
    "ㄾ",
    "ㄿ",
    "ㅀ",
    "ㅁ",
    "ㅂ",
    "ㅄ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]
KOR_DIGIT_WORDS = {
    "0": "공",
    "1": "일",
    "2": "이",
    "3": "삼",
    "4": "사",
    "5": "오",
    "6": "육",
    "7": "칠",
    "8": "팔",
    "9": "구",
}


def _find_zip(raw_dir: Path, keyword: str) -> Optional[Path]:
    candidates = sorted([p for p in raw_dir.glob("*.zip") if keyword in p.name], key=lambda p: p.name)
    if not candidates:
        return None
    return candidates[-1]


def _decode_line(raw: bytes) -> str:
    for enc in ("cp949", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc).rstrip("\r\n")
        except UnicodeDecodeError:
            continue
    return ""


def _is_hangul_syllable(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    return 0xAC00 <= code <= 0xD7A3


def _address_jamo(text: str) -> str:
    out: List[str] = []
    for ch in text:
        if not _is_hangul_syllable(ch):
            out.append(ch)
            continue
        offset = ord(ch) - 0xAC00
        cho = HANGUL_CHO[offset // (21 * 28)]
        jung = HANGUL_JUNG[(offset % (21 * 28)) // 28]
        jong = HANGUL_JONG[offset % 28]
        out.append(cho + jung + jong)
    return "".join(out)


def _address_choseong(text: str) -> str:
    out: List[str] = []
    for ch in text:
        if not _is_hangul_syllable(ch):
            out.append(ch)
            continue
        offset = ord(ch) - 0xAC00
        out.append(HANGUL_CHO[offset // (21 * 28)])
    return "".join(out)


def _address_kr_digits(text: str) -> str:
    return "".join(KOR_DIGIT_WORDS.get(ch, ch) for ch in text)


def _address_zwsp(text: str) -> str:
    out: List[str] = []
    for idx, ch in enumerate(text):
        out.append(ch)
        if ch == " ":
            continue
        if ch.isdigit() or (_is_hangul_syllable(ch) and idx % 2 == 1):
            out.append("\u200b")
    return "".join(out).rstrip("\u200b")


def _address_unit_space_noise(text: str) -> str:
    value = re.sub(r"(\d)\s+(번길|길|로|번지|동|층|호)", r"\1\2", text)
    value = re.sub(r"(번길|길|로|번지|동|층|호)(\d)", r"\1 \2", value)
    value = re.sub(r"([가-힣])\s+(동|리|면|읍)\b", r"\1\2", value)
    return value


def _iter_zip_rows(zip_path: Path, member_prefixes: Sequence[str]) -> Iterable[Tuple[str, List[str]]]:
    with zipfile.ZipFile(zip_path) as zf:
        members = [
            n
            for n in zf.namelist()
            if n.lower().endswith(".txt") and any(Path(n).name.startswith(pfx) for pfx in member_prefixes)
        ]
        for member in members:
            with zf.open(member) as fp:
                for raw in fp:
                    line = _decode_line(raw)
                    if not line or "|" not in line:
                        continue
                    fields = [part.strip() for part in line.split("|")]
                    if len(fields) < 2:
                        continue
                    yield Path(member).name, fields


def _clean_num_token(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch.isdigit())


def _pick_building_no(primary: str, secondary: str, fallback_primary: str, fallback_secondary: str) -> Tuple[str, str]:
    main = _clean_num_token(primary) or _clean_num_token(fallback_primary)
    sub = _clean_num_token(secondary) or _clean_num_token(fallback_secondary)
    if main == "0":
        main = ""
    if sub == "0":
        sub = ""
    return main, sub


def _format_number(main: str, sub: str) -> str:
    if not main:
        return ""
    if not sub:
        return main
    return f"{main}-{sub}"


def _join_nonempty(parts: Sequence[str]) -> str:
    return " ".join([p for p in parts if p]).strip()


def _emd_ri(emd: str, ri: str) -> str:
    if ri and ri != emd:
        return f"{emd} {ri}".strip()
    return emd


def _extract_building_name(fields: Sequence[str]) -> str:
    for idx in (23, 22, 21, 20, 25, 26):
        if idx >= len(fields):
            continue
        value = fields[idx].strip()
        if not value:
            continue
        if any(ch.isdigit() for ch in value) and len(value) <= 2:
            continue
        return value
    return ""


def _stable_index(seed_text: str, size: int) -> int:
    if size <= 0:
        return 0
    return sum(ord(ch) for ch in seed_text) % size


def _parse_road_kor(fields: Sequence[str]) -> Optional[Dict[str, str]]:
    if len(fields) < 17:
        return None
    building_main, building_sub = _pick_building_no(fields[12], fields[13], fields[7], fields[8])
    building_no = _format_number(building_main, building_sub)
    if not (fields[2] and fields[3] and fields[10] and building_no):
        return None
    return {
        "sido": fields[2],
        "sigungu": fields[3],
        "emd": fields[4],
        "ri": fields[5],
        "road_name": fields[10],
        "building_main": building_main,
        "building_sub": building_sub,
        "building_no": building_no,
        "postcode": fields[16],
        "building_name": _extract_building_name(fields),
    }


def _parse_jibun(fields: Sequence[str]) -> Optional[Dict[str, str]]:
    if len(fields) < 9:
        return None
    lot_main = _clean_num_token(fields[7])
    if not lot_main or lot_main == "0":
        return None
    lot_sub = _clean_num_token(fields[8])
    if lot_sub == "0":
        lot_sub = ""
    if not (fields[2] and fields[3] and fields[4]):
        return None
    return {
        "sido": fields[2],
        "sigungu": fields[3],
        "emd": fields[4],
        "ri": fields[5],
        "is_mountain": fields[6],
        "lot_main": lot_main,
        "lot_sub": lot_sub,
    }


def _parse_english_rn(fields: Sequence[str]) -> Optional[Dict[str, str]]:
    if len(fields) < 12:
        return None
    building_no = _format_number(_clean_num_token(fields[9]), _clean_num_token(fields[10]))
    if not (fields[2] and fields[3] and fields[7] and building_no):
        return None
    return {
        "sido_en": fields[2],
        "sigungu_en": fields[3],
        "emd_en": fields[4],
        "road_name_en": fields[7],
        "building_no": building_no,
        "postcode": fields[11],
    }


def _parse_english_db(fields: Sequence[str]) -> Optional[Dict[str, str]]:
    if len(fields) < 15:
        return None
    building_no = _format_number(_clean_num_token(fields[11]), _clean_num_token(fields[12]))
    if not (fields[1] and fields[2] and fields[9] and building_no):
        return None
    return {
        "sido_en": fields[1],
        "sigungu_en": fields[2],
        "emd_en": fields[3],
        "road_name_en": fields[9],
        "building_no": building_no,
        "postcode": fields[14],
    }


def _collect_road_components(raw_dir: Path, rng: random.Random, limit: int) -> List[Dict[str, str]]:
    zip_path = _find_zip(raw_dir, "도로명주소 한글")
    if not zip_path:
        return []
    rows: List[Dict[str, str]] = []
    seen = set()
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if Path(m).name.startswith("rnaddrkor_") and m.endswith(".txt")]
        rng.shuffle(members)
        for member in members:
            with zf.open(member) as fp:
                for raw in fp:
                    line = _decode_line(raw)
                    if not line or "|" not in line:
                        continue
                    parsed = _parse_road_kor([p.strip() for p in line.split("|")])
                    if not parsed:
                        continue
                    key = (
                        parsed["sido"],
                        parsed["sigungu"],
                        parsed["emd"],
                        parsed["ri"],
                        parsed["road_name"],
                        parsed["building_no"],
                        parsed["postcode"],
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(parsed)
                    if len(rows) >= limit:
                        return rows
    return rows


def _collect_jibun_components(raw_dir: Path, rng: random.Random, limit: int) -> List[Dict[str, str]]:
    zip_path = _find_zip(raw_dir, "도로명주소 한글")
    if not zip_path:
        return []
    rows: List[Dict[str, str]] = []
    seen = set()
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if Path(m).name.startswith("jibun_rnaddrkor_") and m.endswith(".txt")]
        rng.shuffle(members)
        for member in members:
            with zf.open(member) as fp:
                for raw in fp:
                    line = _decode_line(raw)
                    if not line or "|" not in line:
                        continue
                    parsed = _parse_jibun([p.strip() for p in line.split("|")])
                    if not parsed:
                        continue
                    key = (
                        parsed["sido"],
                        parsed["sigungu"],
                        parsed["emd"],
                        parsed["ri"],
                        parsed["is_mountain"],
                        parsed["lot_main"],
                        parsed["lot_sub"],
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(parsed)
                    if len(rows) >= limit:
                        return rows
    return rows


def _collect_english_components(raw_dir: Path, rng: random.Random, limit: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen = set()

    rn_zip = _find_zip(raw_dir, "도로명주소 영어")
    if rn_zip:
        with zipfile.ZipFile(rn_zip) as zf:
            members = [m for m in zf.namelist() if Path(m).name.startswith("rneng_") and m.endswith(".txt")]
            rng.shuffle(members)
            for member in members:
                with zf.open(member) as fp:
                    for raw in fp:
                        line = _decode_line(raw)
                        if not line or "|" not in line:
                            continue
                        parsed = _parse_english_rn([p.strip() for p in line.split("|")])
                        if not parsed:
                            continue
                        key = (
                            parsed["sido_en"],
                            parsed["sigungu_en"],
                            parsed["road_name_en"],
                            parsed["building_no"],
                            parsed["postcode"],
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(parsed)
                        if len(rows) >= limit:
                            return rows

    eng_db_zip = _find_zip(raw_dir, "영문주소DB")
    if eng_db_zip:
        with zipfile.ZipFile(eng_db_zip) as zf:
            members = [m for m in zf.namelist() if Path(m).name.startswith("rn_") and m.endswith(".txt")]
            rng.shuffle(members)
            for member in members:
                with zf.open(member) as fp:
                    for raw in fp:
                        line = _decode_line(raw)
                        if not line or "|" not in line:
                            continue
                        parsed = _parse_english_db([p.strip() for p in line.split("|")])
                        if not parsed:
                            continue
                        key = (
                            parsed["sido_en"],
                            parsed["sigungu_en"],
                            parsed["road_name_en"],
                            parsed["building_no"],
                            parsed["postcode"],
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        rows.append(parsed)
                        if len(rows) >= limit:
                            return rows
    return rows


def _collect_special_components(raw_dir: Path, rng: random.Random, limit: int) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    object_zip = _find_zip(raw_dir, "사물주소")
    if object_zip:
        count = 0
        for member, fields in _iter_zip_rows(object_zip, ["Total.JUSUAN.", "TI_SPOT_"]):
            if "_M.TXT" in member and len(fields) >= 6:
                rows.append(
                    {
                        "kind": "object",
                        "sido": fields[4],
                        "sigungu": fields[5],
                        "label": fields[1],
                        "obj_id": fields[0],
                    }
                )
                count += 1
            if count >= max(200, limit // 3):
                break

    postbox_zip = _find_zip(raw_dir, "사서함주소DB")
    if postbox_zip:
        count = 0
        for _, fields in _iter_zip_rows(postbox_zip, ["Postbox_RN_Address_"]):
            if len(fields) >= 12:
                rows.append(
                    {
                        "kind": "postbox",
                        "sido": fields[1],
                        "sigungu": fields[2],
                        "label": fields[9],
                        "num": _format_number(
                            _clean_num_token(fields[11]),
                            _clean_num_token(fields[12] if len(fields) > 12 else ""),
                        ),
                        "postcode": fields[26] if len(fields) > 26 else "",
                    }
                )
                count += 1
            if count >= max(200, limit // 3):
                break

    honor_zip = _find_zip(raw_dir, "명예도로")
    if honor_zip:
        for _, fields in _iter_zip_rows(honor_zip, ["TI_SPRD_HONOR"]):
            if len(fields) >= 5:
                rows.append(
                    {
                        "kind": "honor_road",
                        "sido": "",
                        "sigungu": "",
                        "label": fields[3],
                        "label_en": fields[4],
                    }
                )
            if len(rows) >= limit:
                break

    rng.shuffle(rows)
    return rows[:limit]


def _collect_detail_pools(raw_dir: Path, rng: random.Random) -> Dict[str, List[str]]:
    pools = {"dong": set(), "floor": set(), "ho": set(), "annex": set()}

    detail_zip = _find_zip(raw_dir, "상세주소DB")
    if detail_zip:
        for _, fields in _iter_zip_rows(detail_zip, ["adrdc_"]):
            if len(fields) < 8:
                continue
            annex = fields[5].strip()
            floor = _clean_num_token(fields[6])
            ho = _clean_num_token(fields[7])
            if annex:
                pools["annex"].add(annex)
                if annex.endswith("동"):
                    pools["dong"].add(annex)
            if floor and floor != "0":
                pools["floor"].add(f"{floor}층")
            if ho and ho != "0":
                pools["ho"].add(f"{ho}호")

    display_zip = _find_zip(raw_dir, "상세주소 표시")
    if display_zip:
        for _, fields in _iter_zip_rows(display_zip, ["rnspbd_adrdc_"]):
            if len(fields) < 8:
                continue
            floor = _clean_num_token(fields[6])
            ho = _clean_num_token(fields[7])
            if floor and floor != "0":
                pools["floor"].add(f"{floor}층")
            if ho and ho != "0":
                pools["ho"].add(f"{ho}호")

    dong_zip = _find_zip(raw_dir, "상세주소 동 표시")
    if dong_zip:
        for _, fields in _iter_zip_rows(dong_zip, ["rnspbd_dong_"]):
            if len(fields) < 4:
                continue
            dong = fields[3].strip()
            if dong and (dong.endswith("동") or dong.endswith("관")):
                pools["dong"].add(dong)

    if not pools["floor"]:
        pools["floor"].update(["2층", "3층", "10층", "15층"])
    if not pools["ho"]:
        pools["ho"].update(["101호", "202호", "1203호", "1501호"])

    output: Dict[str, List[str]] = {}
    for key, values in pools.items():
        items = list(values)
        rng.shuffle(items)
        output[key] = items[:3000]
    return output


def _collect_building_names(raw_dir: Path, rng: random.Random) -> List[str]:
    names = set()

    road_zip = _find_zip(raw_dir, "도로명주소 한글")
    if road_zip:
        for _, fields in _iter_zip_rows(road_zip, ["rnaddrkor_"]):
            name = _extract_building_name(fields)
            if name:
                names.add(name)
            if len(names) >= 10000:
                break

    building_zip = _find_zip(raw_dir, "건물DB")
    if building_zip:
        for _, fields in _iter_zip_rows(building_zip, ["build_"]):
            name = _extract_building_name(fields)
            if name:
                names.add(name)
            if len(names) >= 20000:
                break

    items = list(names)
    rng.shuffle(items)
    return items[:10000]


def _compose_road_address(base: Dict[str, str], abbreviated: bool = False) -> str:
    sido = base.get("sido", "")
    if abbreviated:
        sido = KOR_SIDO_ABBREV.get(sido, sido)
    return _join_nonempty(
        [
            sido,
            base.get("sigungu", ""),
            _emd_ri(base.get("emd", ""), base.get("ri", "")),
            base.get("road_name", ""),
            base.get("building_no", ""),
        ]
    )


def _compose_jibun_address(base: Dict[str, str], abbreviated: bool = False) -> str:
    sido = base.get("sido", "")
    if abbreviated:
        sido = KOR_SIDO_ABBREV.get(sido, sido)
    lot_no = _format_number(base.get("lot_main", ""), base.get("lot_sub", ""))
    if base.get("is_mountain") == "1":
        lot_no = f"산 {lot_no}".strip()
    return _join_nonempty(
        [
            sido,
            base.get("sigungu", ""),
            _emd_ri(base.get("emd", ""), base.get("ri", "")),
            lot_no,
        ]
    )


def _build_detail_fragment(detail_pools: Dict[str, List[str]], seed_text: str) -> str:
    parts: List[str] = []
    dong_pool = detail_pools.get("dong", [])
    floor_pool = detail_pools.get("floor", [])
    ho_pool = detail_pools.get("ho", [])
    annex_pool = detail_pools.get("annex", [])

    if dong_pool:
        parts.append(dong_pool[_stable_index(seed_text + ":dong", len(dong_pool))])
    elif annex_pool:
        parts.append(annex_pool[_stable_index(seed_text + ":annex", len(annex_pool))])
    if floor_pool:
        parts.append(floor_pool[_stable_index(seed_text + ":floor", len(floor_pool))])
    if ho_pool:
        parts.append(ho_pool[_stable_index(seed_text + ":ho", len(ho_pool))])
    if not parts:
        parts = ["101동", "1203호"]
    return " ".join(parts).strip()


def _expected_action(tier: str, mutation_name: str) -> str:
    if mutation_name in CONTEXT_PREFIXES:
        return "mask"
    return EXPECTED_ACTION_BY_TIER.get(tier, "maybe_mask")


def _cap_records_by_tier(records: List[Dict[str, object]], max_records: int, rng: random.Random) -> List[Dict[str, object]]:
    if max_records <= 0 or len(records) <= max_records:
        return records
    buckets: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for rec in records:
        buckets[str(rec.get("primary_tier", ""))].append(rec)
    for arr in buckets.values():
        rng.shuffle(arr)

    selected: List[Dict[str, object]] = []
    tiers = sorted(buckets.keys())
    while len(selected) < max_records:
        progressed = False
        for tier in tiers:
            if buckets[tier]:
                selected.append(buckets[tier].pop())
                progressed = True
                if len(selected) >= max_records:
                    break
        if not progressed:
            break
    return selected


def _road_tags(base: Dict[str, str], with_detail: bool = False, with_postcode: bool = False, with_building: bool = False) -> List[str]:
    tags = ["system_road", "precision_road_building", "has_road_name", "has_building_number"]
    if base.get("postcode"):
        tags.append("has_postcode")
    if with_postcode:
        tags.append("postcode_prefix")
    if with_detail:
        tags.extend(["has_detail", "precision_unit"])
    if with_building:
        tags.extend(["has_building_name", "building_named"])
    if base.get("sido") in KOR_SIDO_ABBREV:
        tags.append("admin_full")
    return sorted(set(tags))


def _jibun_tags(base: Dict[str, str], with_detail: bool = False) -> List[str]:
    tags = ["system_jibun", "has_lot_number", "precision_lot"]
    if base.get("is_mountain") == "1":
        tags.append("has_mountain_lot")
    if with_detail:
        tags.extend(["has_detail", "precision_unit"])
    return sorted(set(tags))


def _english_tags(mixed: bool = False) -> List[str]:
    tags = ["system_english", "script_latin", "precision_road_building"]
    if mixed:
        tags.extend(["system_mixed", "script_mixed"])
    return sorted(set(tags))


def _special_tags(kind: str) -> List[str]:
    return sorted(set(["system_special", f"special_{kind}"]))


def build_tagged_address_records(raw_dir: str, seed: int = 42, max_records: int = 50000) -> List[Dict[str, object]]:
    raw_path = Path(raw_dir)
    rng = random.Random(seed)
    road_components = _collect_road_components(raw_path, rng, limit=max_records * 3)
    jibun_components = _collect_jibun_components(raw_path, rng, limit=max_records * 2)
    english_components = _collect_english_components(raw_path, rng, limit=max_records)
    special_components = _collect_special_components(raw_path, rng, limit=max(1000, max_records // 2))
    detail_pools = _collect_detail_pools(raw_path, rng)
    building_names = _collect_building_names(raw_path, rng)

    records: List[Dict[str, object]] = []
    dedupe = set()

    def add_rec(
        tier: str,
        system: str,
        full: str,
        tags: Sequence[str],
        comps: Dict[str, str],
        datasets: Sequence[str],
    ) -> None:
        if not full:
            return
        key = (tier, full)
        if key in dedupe:
            return
        dedupe.add(key)
        records.append(
            {
                "address_id": "",
                "full_address": full,
                "primary_tier": tier,
                "address_system": system,
                "address_tags": sorted(set(tags)),
                "components": comps,
                "source": {"datasets": list(datasets), "synthetic": True},
                "synthetic": True,
            }
        )

    for idx, base in enumerate(road_components):
        seed_text = f"road:{idx}:{base.get('road_name','')}:{base.get('building_no','')}"
        road_addr = _compose_road_address(base, abbreviated=False)
        add_rec(
            "A1_road_basic",
            "road",
            road_addr,
            _road_tags(base),
            {
                "sido": base.get("sido", ""),
                "sigungu": base.get("sigungu", ""),
                "emd": base.get("emd", ""),
                "ri": base.get("ri", ""),
                "road_name": base.get("road_name", ""),
                "building_no": base.get("building_no", ""),
                "postcode": base.get("postcode", ""),
            },
            ["도로명주소 한글"],
        )
        detail = _build_detail_fragment(detail_pools, seed_text)
        add_rec(
            "A2_road_detail",
            "road",
            f"{road_addr}, {detail}",
            _road_tags(base, with_detail=True),
            {
                "sido": base.get("sido", ""),
                "sigungu": base.get("sigungu", ""),
                "emd": base.get("emd", ""),
                "ri": base.get("ri", ""),
                "road_name": base.get("road_name", ""),
                "building_no": base.get("building_no", ""),
                "postcode": base.get("postcode", ""),
                "detail": detail,
            },
            ["도로명주소 한글", "상세주소DB"],
        )
        if base.get("postcode"):
            add_rec(
                "A5_postcode_road",
                "postcode",
                f"{base['postcode']} {road_addr}",
                _road_tags(base, with_postcode=True),
                {
                    "postcode": base.get("postcode", ""),
                    "sido": base.get("sido", ""),
                    "sigungu": base.get("sigungu", ""),
                    "road_name": base.get("road_name", ""),
                    "building_no": base.get("building_no", ""),
                },
                ["도로명주소 한글"],
            )
        add_rec(
            "A6_abbrev_noisy",
            "road",
            _compose_road_address(base, abbreviated=True).replace(" ", ""),
            sorted(set(_road_tags(base) + ["admin_abbrev", "spacing_missing", "compact_building_no"])),
            {
                "sido": KOR_SIDO_ABBREV.get(base.get("sido", ""), base.get("sido", "")),
                "sigungu": base.get("sigungu", ""),
                "road_name": base.get("road_name", ""),
                "building_no": base.get("building_no", ""),
            },
            ["도로명주소 한글"],
        )
        bname = base.get("building_name", "")
        if not bname and building_names:
            bname = building_names[_stable_index(seed_text + ":bname", len(building_names))]
        if bname:
            add_rec(
                "A8_building_named",
                "road",
                f"{road_addr} {bname}",
                _road_tags(base, with_building=True),
                {
                    "sido": base.get("sido", ""),
                    "sigungu": base.get("sigungu", ""),
                    "road_name": base.get("road_name", ""),
                    "building_no": base.get("building_no", ""),
                    "building_name": bname,
                },
                ["도로명주소 한글", "건물DB"],
            )

    for idx, base in enumerate(jibun_components):
        seed_text = f"jibun:{idx}:{base.get('emd','')}:{base.get('lot_main','')}"
        jibun_addr = _compose_jibun_address(base, abbreviated=False)
        add_rec(
            "A3_jibun_basic",
            "jibun",
            jibun_addr,
            _jibun_tags(base),
            {
                "sido": base.get("sido", ""),
                "sigungu": base.get("sigungu", ""),
                "emd": base.get("emd", ""),
                "ri": base.get("ri", ""),
                "is_mountain": base.get("is_mountain", ""),
                "lot_no": _format_number(base.get("lot_main", ""), base.get("lot_sub", "")),
            },
            ["도로명주소 한글"],
        )
        detail = _build_detail_fragment(detail_pools, seed_text)
        bname = building_names[_stable_index(seed_text + ":bname", len(building_names))] if building_names else ""
        suffix = f"{bname} {detail}".strip() if bname else detail
        add_rec(
            "A4_jibun_detail",
            "jibun",
            f"{jibun_addr} {suffix}".strip(),
            sorted(set(_jibun_tags(base, with_detail=True) + (["has_building_name"] if bname else []))),
            {
                "sido": base.get("sido", ""),
                "sigungu": base.get("sigungu", ""),
                "emd": base.get("emd", ""),
                "ri": base.get("ri", ""),
                "is_mountain": base.get("is_mountain", ""),
                "lot_no": _format_number(base.get("lot_main", ""), base.get("lot_sub", "")),
                "detail": detail,
                "building_name": bname,
            },
            ["도로명주소 한글", "상세주소DB", "건물DB"],
        )

    for base in english_components:
        eng_addr = _join_nonempty(
            [base.get("building_no", ""), f"{base.get('road_name_en', '')},", base.get("sigungu_en", ""), base.get("sido_en", "")]
        ).replace(" ,", ",")
        add_rec(
            "A7_english_mixed",
            "english",
            eng_addr,
            _english_tags(mixed=False),
            {
                "sido_en": base.get("sido_en", ""),
                "sigungu_en": base.get("sigungu_en", ""),
                "emd_en": base.get("emd_en", ""),
                "road_name_en": base.get("road_name_en", ""),
                "building_no": base.get("building_no", ""),
                "postcode": base.get("postcode", ""),
            },
            ["도로명주소 영어", "영문주소DB"],
        )
        add_rec(
            "A7_english_mixed",
            "mixed",
            f"{KOR_SIDO_ABBREV.get('서울특별시', '서울')} {base.get('road_name_en', '')} {base.get('building_no', '')}".strip(),
            _english_tags(mixed=True),
            {"road_name_en": base.get("road_name_en", ""), "building_no": base.get("building_no", "")},
            ["도로명주소 영어", "영문주소DB", "도로명"],
        )

    for item in special_components:
        kind = item.get("kind", "")
        if kind == "object":
            full = _join_nonempty([item.get("sido", ""), item.get("sigungu", ""), item.get("label", ""), item.get("obj_id", "")])
            add_rec(
                "A9_special_address",
                "special",
                full,
                _special_tags("object"),
                {"kind": kind, "sido": item.get("sido", ""), "sigungu": item.get("sigungu", ""), "label": item.get("label", "")},
                ["사물주소"],
            )
        elif kind == "postbox":
            full = _join_nonempty([item.get("sido", ""), item.get("sigungu", ""), item.get("label", ""), item.get("num", "")])
            add_rec(
                "A9_special_address",
                "special",
                full,
                _special_tags("postbox"),
                {
                    "kind": kind,
                    "sido": item.get("sido", ""),
                    "sigungu": item.get("sigungu", ""),
                    "label": item.get("label", ""),
                    "postcode": item.get("postcode", ""),
                },
                ["사서함주소DB"],
            )
        elif kind == "honor_road":
            add_rec(
                "A9_special_address",
                "special",
                f"{item.get('label', '')} (명예도로)".strip(),
                _special_tags("honor_road"),
                {"kind": kind, "label": item.get("label", ""), "label_en": item.get("label_en", "")},
                ["명예도로"],
            )

    capped = _cap_records_by_tier(records, max_records=max_records, rng=rng)
    for idx, row in enumerate(capped, start=1):
        row["address_id"] = f"kra_{idx:06d}"
    return capped


def load_tagged_address_records(path: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if "full_address" not in item:
                continue
            item.setdefault("address_id", "")
            item.setdefault("primary_tier", "A1_road_basic")
            item.setdefault("address_system", "road")
            item.setdefault("address_tags", [])
            item.setdefault("components", {})
            item.setdefault("synthetic", True)
            rows.append(item)
    return rows


def load_address_seed_records(path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                continue
            seed_id = str(item.get("id", "")).strip()
            text = str(
                item.get("text")
                or item.get("mutated")
                or item.get("mutated_address")
                or item.get("full_address")
                or ""
            ).strip()
            if not text:
                continue
            rows.append({"id": seed_id, "text": text})
    return rows


def build_korean_address_mutations(record: Dict[str, object]) -> List[Dict[str, object]]:
    full = str(record.get("full_address", "")).strip()
    if not full:
        return []

    comps = record.get("components", {}) if isinstance(record.get("components"), dict) else {}
    address_system = str(record.get("address_system", "")).strip()
    postcode = str(comps.get("postcode", "")).strip()
    road_name = str(comps.get("road_name", "")).strip()
    building_no = str(comps.get("building_no", "")).strip()
    detail = str(comps.get("detail", "")).strip()
    building_name = str(comps.get("building_name", "")).strip()
    sido = str(comps.get("sido", "")).strip()
    road_name_en = str(comps.get("road_name_en", "")).strip()

    seen = set()
    out: List[Dict[str, object]] = []

    def add(name: str, value: str, tags: Sequence[str]) -> None:
        value = value.strip()
        if not value or value == full:
            return
        key = (name, value)
        if key in seen:
            return
        seen.add(key)
        out.append({"mutation_name": name, "mutated_address": value, "mutation_tags": list(tags)})

    if sido and sido in KOR_SIDO_ABBREV:
        add("admin_abbrev", full.replace(sido, KOR_SIDO_ABBREV[sido], 1), ["admin_abbrev"])
        add("drop_sido", full.replace(f"{sido} ", "", 1), ["drop_sido", "admin_omitted"])

    add("remove_comma", full.replace(", ", " ").replace(",", ""), ["comma_missing"])
    add("remove_spaces", full.replace(" ", ""), ["spacing_missing"])

    if road_name and building_no:
        add(
            "compact_building_no",
            full.replace(f"{road_name} {building_no}", f"{road_name}{building_no}"),
            ["compact_building_no", "spacing_missing"],
        )

    if postcode:
        add("postcode_prefix", f"{postcode} {full}", ["postcode_prefix"])
        add("postcode_suffix", f"{full} ({postcode})", ["postcode_suffix"])

    if detail:
        add("detail_first", f"{detail}, {full}", ["detail_first"])
    if building_name:
        add("building_name_first", f"{building_name}, {full}", ["building_name_first", "has_building_name"])

    if address_system == "jibun" and "번지" not in full and any(ch.isdigit() for ch in full):
        add("jibun_beonji_suffix", f"{full}번지", ["jibun_beonji_suffix"])

    add("address_choseong", _address_choseong(full), ["address_linguistic", "choseong"])
    add("address_jamo", _address_jamo(full), ["address_linguistic", "jamo"])
    add("address_kr_digits", _address_kr_digits(full), ["address_linguistic", "kr_digits"])
    add("address_zwsp", _address_zwsp(full), ["address_linguistic", "zero_width"])
    add(
        "address_unit_space_noise",
        _address_unit_space_noise(full),
        ["address_linguistic", "unit_spacing_noise"],
    )

    for m_name, prefix in CONTEXT_PREFIXES.items():
        add(m_name, f"{prefix}{full}", [m_name, "contextual"])

    if road_name_en:
        add("mixed_english", f"{full} ({road_name_en})", ["mixed_english", "script_mixed"])
        sigungu_en = str(comps.get("sigungu_en", "")).strip()
        sido_en = str(comps.get("sido_en", "")).strip()
        if building_no and sigungu_en and sido_en:
            add(
                "english_order",
                f"{building_no}, {road_name_en}, {sigungu_en}, {sido_en}",
                ["english_order", "script_latin"],
            )

    return out


def build_expanded_address_mutation_records(
    records: Sequence[Dict[str, object]],
    per_record: int = 0,
    seed: int = 42,
) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    out: List[Dict[str, object]] = []
    seq = 0

    for rec in records:
        address_id = str(rec.get("address_id", ""))
        tier = str(rec.get("primary_tier", "A1_road_basic"))
        full = str(rec.get("full_address", ""))
        address_tags = list(rec.get("address_tags", []))
        mutations = [{"mutation_name": "official", "mutated_address": full, "mutation_tags": ["official"]}]
        mutations.extend(build_korean_address_mutations(rec))

        if per_record > 0 and len(mutations) > per_record:
            picked = [mutations[0]]
            if per_record > 1:
                picked.extend(rng.sample(mutations[1:], k=per_record - 1))
            mutations = picked

        for item in mutations:
            seq += 1
            mutation_name = str(item["mutation_name"])
            mutated_address = str(item["mutated_address"])
            mutation_tags = list(item.get("mutation_tags", [mutation_name]))
            out.append(
                {
                    "id": f"ADR-{seq:06d}",
                    "address_id": address_id,
                    "address_tier": tier,
                    "address_system": rec.get("address_system", ""),
                    "address_tags": address_tags,
                    "original_address": full,
                    "mutated_address": mutated_address,
                    "mutation_name": mutation_name,
                    "mutation_tags": mutation_tags,
                    "expected_action": _expected_action(tier, mutation_name),
                    "original": full,
                    "mutated": mutated_address,
                    "synthetic": True,
                }
            )
    return out


def build_balanced_address_sample(
    records: Sequence[Dict[str, object]],
    per_tier: int,
    seed: int = 42,
) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in records:
        buckets[str(row.get("primary_tier", "A1_road_basic"))].append(row)
    sampled: List[Dict[str, object]] = []
    for tier in sorted(buckets.keys()):
        bucket = buckets[tier]
        rng.shuffle(bucket)
        sampled.extend(bucket[:per_tier])
    rng.shuffle(sampled)
    return sampled


def summarize_address_records(records: Sequence[Dict[str, object]]) -> Dict[str, object]:
    by_tier: Counter = Counter()
    by_system: Counter = Counter()
    by_tag: Counter = Counter()
    for row in records:
        by_tier[str(row.get("primary_tier", ""))] += 1
        by_system[str(row.get("address_system", ""))] += 1
        for tag in row.get("address_tags", []):
            by_tag[str(tag)] += 1
    return {
        "total": len(records),
        "by_primary_tier": dict(sorted(by_tier.items())),
        "by_system": dict(sorted(by_system.items())),
        "top_tags": dict(by_tag.most_common(50)),
    }


def write_jsonl(records: Iterable[Dict[str, object]], output_path: str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fp:
        for row in records:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(summary: Dict[str, object], output_path: str) -> None:
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

"""
Synthetic hospital-style medical record number generator.

This module intentionally does NOT model any private real-world hospital MRN rule.
It provides synthetic institution-style patterns with explicit specs + validators.

Important validity boundary:
- Korean MRNs do not have one public nationwide format/checksum like RRNs.
- The "valid" result here means "valid against this module's synthetic
  hospital-style spec", not "verified against a real hospital system".
- Do not replace these specs with guessed private hospital rules or real patient
  identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import re


@dataclass(frozen=True)
class HospitalMRNSpec:
    hospital_key: str
    display_name: str
    hospital_code: str
    pattern_name: str
    dept_codes: tuple[str, ...]
    year_range: tuple[int, int]
    serial_digits: int
    check_algorithm: str


@dataclass(frozen=True)
class MedicalRecordNumber:
    value: str
    hospital_key: str
    hospital_name: str
    hospital_code: str
    pattern_name: str
    year: int
    dept_code: str
    serial: str
    check_digit: str
    synthetic: bool = True
    rule_valid: bool = True


# Synthetic institution-style specs. Names/codes are used only as plausible
# hospital-context labels for security testing; the patterns are not asserted to
# be real hospital-internal MRN rules.
HOSPITAL_MRN_SPECS: list[HospitalMRNSpec] = [
    HospitalMRNSpec(
        hospital_key="snuh",
        display_name="서울대병원",
        hospital_code="SNUH",
        pattern_name="CODE-YYYY-DEPT-SERIAL-CHECK",
        dept_codes=("IM", "GS", "NEU", "PED", "ER", "DER", "ENT", "PSY"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="mod11",
    ),
    HospitalMRNSpec(
        hospital_key="sev",
        display_name="세브란스병원",
        hospital_code="SEV",
        pattern_name="CODE-YY-DEPT-SERIAL-CHECK",
        dept_codes=("ONC", "IM", "GS", "ENT", "PSY", "PED", "OBG"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="mod11x",
    ),
    HospitalMRNSpec(
        hospital_key="smc",
        display_name="삼성서울병원",
        hospital_code="SMC",
        pattern_name="CODE-YYYYMM-DEPT-SERIAL-CHECK",
        dept_codes=("ER", "IM", "NEU", "OBG", "PED", "ONC", "CAR"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="luhn",
    ),
    HospitalMRNSpec(
        hospital_key="amc",
        display_name="서울아산병원",
        hospital_code="AMC",
        pattern_name="CODE-YYYY-DEPT-SERIAL-CHECK",
        dept_codes=("PED", "IM", "GS", "ORTH", "ER", "CAR", "NEU"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="luhn",
    ),
    HospitalMRNSpec(
        hospital_key="cmc",
        display_name="서울성모병원",
        hospital_code="CMC",
        pattern_name="CODE-YY-DEPT-SERIAL-CHECK",
        dept_codes=("IM", "GS", "ONC", "ENT", "DER", "PSY"),
        year_range=(2018, 2026),
        serial_digits=5,
        check_algorithm="mod11",
    ),
    HospitalMRNSpec(
        hospital_key="cnuh",
        display_name="충남대병원",
        hospital_code="CNUH",
        pattern_name="CODE-YYYYMM-DEPT-SERIAL-CHECK",
        dept_codes=("IM", "GS", "NEU", "PED", "FM", "ER"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="mod11x",
    ),
    HospitalMRNSpec(
        hospital_key="knuh",
        display_name="경북대병원",
        hospital_code="KNUH",
        pattern_name="CODE-YYYY-DEPT-SERIAL-CHECK",
        dept_codes=("ER", "IM", "GS", "OBG", "PSY", "NEU"),
        year_range=(2018, 2026),
        serial_digits=7,
        check_algorithm="luhn",
    ),
    HospitalMRNSpec(
        hospital_key="jnuh",
        display_name="전남대병원",
        hospital_code="JNUH",
        pattern_name="CODE-YY-DEPT-SERIAL-CHECK",
        dept_codes=("IM", "GS", "DER", "ENT", "PED", "FM"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="mod11",
    ),
    HospitalMRNSpec(
        hospital_key="pnuh",
        display_name="부산대병원",
        hospital_code="PNUH",
        pattern_name="CODE-YYYYMM-DEPT-SERIAL-CHECK",
        dept_codes=("IM", "GS", "ER", "NEU", "FM", "ONC"),
        year_range=(2018, 2026),
        serial_digits=6,
        check_algorithm="luhn",
    ),
    HospitalMRNSpec(
        hospital_key="kuam",
        display_name="고려대안암병원",
        hospital_code="KUAM",
        pattern_name="CODE-YYYY-DEPT-SERIAL-CHECK",
        dept_codes=("ONC", "IM", "GS", "PED", "ORTH", "ENT"),
        year_range=(2018, 2026),
        serial_digits=5,
        check_algorithm="mod11",
    ),
]


_SPECS_BY_KEY = {spec.hospital_key: spec for spec in HOSPITAL_MRN_SPECS}
_SPECS_BY_CODE = {spec.hospital_code: spec for spec in HOSPITAL_MRN_SPECS}


def _collapse_ws(text: str) -> str:
    return " ".join(str(text).split())


def _normalize_check_payload(payload: str) -> str:
    return "".join(ch for ch in payload.upper() if ch.isalnum())


def _char_to_int(ch: str) -> int:
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "A" <= ch <= "Z":
        return ord(ch) - ord("A") + 10
    raise ValueError(f"Unsupported character for check algorithm: {ch}")


def _to_luhn_digits(payload: str) -> str:
    normalized = _normalize_check_payload(payload)
    out = []
    for ch in normalized:
        if ch.isdigit():
            out.append(ch)
        else:
            out.append(f"{_char_to_int(ch):02d}")
    return "".join(out)


def _luhn_check_digit(base_digits: str) -> str:
    total = 0
    for idx, ch in enumerate(reversed(base_digits), start=1):
        n = int(ch)
        if idx % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return str((10 - (total % 10)) % 10)


def _mod11_check_digit(payload: str, allow_x: bool) -> str:
    normalized = _normalize_check_payload(payload)
    total = 0
    weight = 2
    for ch in reversed(normalized):
        total += _char_to_int(ch) * weight
        weight = 2 if weight == 7 else weight + 1
    check = (11 - (total % 11)) % 11
    if check == 10:
        return "X" if allow_x else "0"
    return str(check)


def calculate_check_digit(payload: str, algorithm: str) -> str:
    algo = algorithm.lower().strip()
    if algo == "luhn":
        return _luhn_check_digit(_to_luhn_digits(payload))
    if algo == "mod11":
        return _mod11_check_digit(payload, allow_x=False)
    if algo == "mod11x":
        return _mod11_check_digit(payload, allow_x=True)
    raise ValueError(f"Unsupported check algorithm: {algorithm}")


def _year_token_digits(spec: HospitalMRNSpec) -> int:
    name = spec.pattern_name.upper()
    if "YYYYMM" in name:
        return 6
    if "YYYY" in name:
        return 4
    if "YY" in name:
        return 2
    raise ValueError(f"Unsupported pattern_name: {spec.pattern_name}")


def _make_year_token(spec: HospitalMRNSpec, year: int, rng: random.Random) -> str:
    digits = _year_token_digits(spec)
    if digits == 6:
        month = rng.randint(1, 12)
        return f"{year:04d}{month:02d}"
    if digits == 4:
        return f"{year:04d}"
    if digits == 2:
        return f"{year % 100:02d}"
    raise ValueError(f"Unsupported year token digits: {digits}")


def _parse_year_from_token(spec: HospitalMRNSpec, year_token: str) -> tuple[int, bool]:
    digits = _year_token_digits(spec)
    if digits == 6:
        year = int(year_token[:4])
        month = int(year_token[4:6])
        return year, 1 <= month <= 12
    if digits == 4:
        return int(year_token), True
    if digits == 2:
        return 2000 + int(year_token), True
    return 0, False


def _validate_with_spec(value: str, spec: HospitalMRNSpec) -> bool:
    year_digits = _year_token_digits(spec)
    serial_digits = int(spec.serial_digits)
    if serial_digits <= 0:
        return False
    pattern = (
        rf"^{re.escape(spec.hospital_code)}-"
        rf"(\d{{{year_digits}}})-"
        rf"([A-Z]{{2,4}})-"
        rf"(\d{{{serial_digits}}})-"
        rf"([0-9X])$"
    )
    match = re.fullmatch(pattern, value.strip().upper())
    if not match:
        return False

    year_token, dept_code, serial, check_digit = match.groups()
    if dept_code not in spec.dept_codes:
        return False

    year, month_ok = _parse_year_from_token(spec, year_token)
    if not month_ok:
        return False
    if not (spec.year_range[0] <= year <= spec.year_range[1]):
        return False

    payload = f"{spec.hospital_code}{year_token}{dept_code}{serial}"
    expected_check = calculate_check_digit(payload, spec.check_algorithm)
    return expected_check == check_digit


def validate_medical_record_number(value: str, spec: HospitalMRNSpec | None = None) -> bool:
    """Validate an MRN against the synthetic specs defined in this module.

    This deliberately does not claim real-world MRN validity. A True result only
    means the value matches one synthetic hospital-style pattern and check digit.
    """
    if not value or not isinstance(value, str):
        return False
    if spec is not None:
        return _validate_with_spec(value, spec)

    prefix = value.strip().upper().split("-", 1)[0]
    candidate = _SPECS_BY_CODE.get(prefix)
    if candidate is not None:
        return _validate_with_spec(value, candidate)
    return any(_validate_with_spec(value, mrn_spec) for mrn_spec in HOSPITAL_MRN_SPECS)


def _parse_value_with_spec(value: str, spec: HospitalMRNSpec) -> tuple[str, str, str, str] | None:
    year_digits = _year_token_digits(spec)
    serial_digits = int(spec.serial_digits)
    pattern = (
        rf"^{re.escape(spec.hospital_code)}-"
        rf"(\d{{{year_digits}}})-"
        rf"([A-Z]{{2,4}})-"
        rf"(\d{{{serial_digits}}})-"
        rf"([0-9X])$"
    )
    match = re.fullmatch(pattern, str(value).strip().upper())
    if not match:
        return None
    return match.groups()


def resolve_medical_record_record(value: str) -> MedicalRecordNumber | None:
    """Resolve a canonical MRN string to structured synthetic record metadata."""
    text = str(value).strip().upper()
    if not text:
        return None

    prefix = text.split("-", 1)[0]
    candidates: list[HospitalMRNSpec]
    prefixed = _SPECS_BY_CODE.get(prefix)
    if prefixed is not None:
        candidates = [prefixed]
    else:
        candidates = list(HOSPITAL_MRN_SPECS)

    for spec in candidates:
        if not _validate_with_spec(text, spec):
            continue
        parsed = _parse_value_with_spec(text, spec)
        if parsed is None:
            continue
        year_token, dept_code, serial, check_digit = parsed
        year, _ = _parse_year_from_token(spec, year_token)
        return MedicalRecordNumber(
            value=text,
            hospital_key=spec.hospital_key,
            hospital_name=spec.display_name,
            hospital_code=spec.hospital_code,
            pattern_name=spec.pattern_name,
            year=year,
            dept_code=dept_code,
            serial=serial,
            check_digit=check_digit,
            synthetic=True,
            rule_valid=True,
        )
    return None


def build_medical_record_korean_mutations(
    record_or_value: MedicalRecordNumber | str,
    name: str = "",
) -> list[dict[str, object]]:
    """
    Build Korean hospital-workflow style mutations for one canonical synthetic MRN.

    Mutation families are intentionally explicit so guardrail coverage can be traced:
    - L4 label variants: 의료기록번호/의무기록번호/환자번호/MRN 등 라벨 치환
    - L4 structured renderings: field split, log, json, csv
    - L4 separator variants: space/slash/compact
    - L5 context templates: EMR/접수/예약/검사조회/처방조회 문맥

    Important: this does not infer any private real-hospital rule. It only re-renders
    the already-validated synthetic MRN (`CODE-...-CHECK`) into Korean workflow text.
    """
    if isinstance(record_or_value, MedicalRecordNumber):
        rec = record_or_value
    else:
        rec = resolve_medical_record_record(str(record_or_value))
        if rec is None:
            return []

    tokens = rec.value.split("-")
    if len(tokens) != 5:
        return []

    hospital_code, year_token, dept_code, serial, check_digit = tokens
    caller = str(name).strip()
    out: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    def add(mutation_name: str, mutated_text: str, mutation_level: int, mutation_tags: list[str]) -> None:
        text = _collapse_ws(mutated_text)
        key = (mutation_name, text)
        if not text or key in seen:
            return
        seen.add(key)
        out.append(
            {
                "mutation_name": mutation_name,
                "mutated_text": text,
                "mutation_level": int(mutation_level),
                "mutation_tags": list(mutation_tags),
            }
        )

    # 1) Label vocabulary drift in Korean healthcare workflows.
    label_variants = [
        "의료기록번호",
        "의무기록번호",
        "환자번호",
        "등록번호",
        "차트번호",
        "EMR No.",
        "MRN",
    ]
    for label in label_variants:
        add(
            f"medical_rec_label_{label}",
            f"{label}: {rec.value}",
            4,
            ["medical_record_korean", "label_variant", label],
        )

    # 2) Structured field renderings that keep all MRN components visible.
    add(
        "medical_rec_field_split",
        (
            f"병원코드: {hospital_code} / 등록연도: {year_token} / 진료과: {dept_code} "
            f"/ 일련번호: {serial} / 검증값: {check_digit}"
        ),
        4,
        ["medical_record_korean", "field_split"],
    )
    add(
        "medical_rec_log_style",
        (
            f"mrn=\"{rec.value}\" hospital_code={hospital_code} year_token={year_token} "
            f"dept={dept_code} serial={serial} check_digit={check_digit}"
        ),
        4,
        ["medical_record_korean", "log_style"],
    )
    add(
        "medical_rec_json_style",
        (
            f'{{"medical_rec":"{rec.value}","hospital_code":"{hospital_code}","year_token":"{year_token}",'
            f'"dept_code":"{dept_code}","serial":"{serial}","check_digit":"{check_digit}"}}'
        ),
        4,
        ["medical_record_korean", "json_style"],
    )
    add(
        "medical_rec_csv_row",
        (
            "medical_rec,hospital_code,year_token,dept_code,serial,check_digit\n"
            f"{rec.value},{hospital_code},{year_token},{dept_code},{serial},{check_digit}"
        ),
        4,
        ["medical_record_korean", "csv_style"],
    )
    # 3) Separator and compact formatting drift around the same components.
    add(
        "medical_rec_sep_space",
        f"{hospital_code} {year_token} {dept_code} {serial} {check_digit}",
        4,
        ["medical_record_korean", "separator", "space"],
    )
    add(
        "medical_rec_sep_slash",
        f"{hospital_code}/{year_token}/{dept_code}/{serial}/{check_digit}",
        4,
        ["medical_record_korean", "separator", "slash"],
    )
    add(
        "medical_rec_compact",
        f"{hospital_code}{year_token}{dept_code}{serial}{check_digit}",
        4,
        ["medical_record_korean", "separator", "compact"],
    )

    # 4) L5 natural-language contexts commonly seen in Korean EMR operations.
    if caller:
        add(
            "medical_rec_ctx_emr",
            f"EMR 조회 결과, {caller} 환자의 의료기록번호는 {rec.value}입니다.",
            5,
            ["medical_record_korean", "context", "emr"],
        )
        add(
            "medical_rec_ctx_reception",
            f"접수 등록번호 확인: {caller} 환자번호 {rec.value}",
            5,
            ["medical_record_korean", "context", "reception"],
        )
        add(
            "medical_rec_ctx_appointment",
            f"진료예약 확인, {caller}님 차트번호 {rec.value}",
            5,
            ["medical_record_korean", "context", "appointment"],
        )
        add(
            "medical_rec_ctx_lab_lookup",
            f"검사결과 조회 요청: 환자명 {caller}, MRN {rec.value}",
            5,
            ["medical_record_korean", "context", "lab_lookup"],
        )
        add(
            "medical_rec_ctx_prescription_lookup",
            f"처방내역 조회: {caller} 환자 의료기록번호 {rec.value}",
            5,
            ["medical_record_korean", "context", "prescription_lookup"],
        )
    else:
        add(
            "medical_rec_ctx_emr",
            f"EMR 조회 결과, 의료기록번호는 {rec.value}입니다.",
            5,
            ["medical_record_korean", "context", "emr"],
        )
        add(
            "medical_rec_ctx_reception",
            f"접수 등록번호 확인: 환자번호 {rec.value}",
            5,
            ["medical_record_korean", "context", "reception"],
        )
        add(
            "medical_rec_ctx_appointment",
            f"진료예약 확인, 차트번호 {rec.value}",
            5,
            ["medical_record_korean", "context", "appointment"],
        )
        add(
            "medical_rec_ctx_lab_lookup",
            f"검사결과 조회 요청: MRN {rec.value}",
            5,
            ["medical_record_korean", "context", "lab_lookup"],
        )
        add(
            "medical_rec_ctx_prescription_lookup",
            f"처방내역 조회: 의료기록번호 {rec.value}",
            5,
            ["medical_record_korean", "context", "prescription_lookup"],
        )

    return out


def generate_medical_record_number(
    hospital_key: str | None = None,
    rng: random.Random | None = None,
) -> MedicalRecordNumber:
    """Generate a synthetic MRN record with traceable spec metadata."""
    picker = rng if rng is not None else random
    if hospital_key:
        spec = _SPECS_BY_KEY.get(hospital_key)
        if spec is None:
            raise ValueError(f"Unknown hospital_key: {hospital_key}")
    else:
        spec = picker.choice(HOSPITAL_MRN_SPECS)

    year = picker.randint(spec.year_range[0], spec.year_range[1])
    year_token = _make_year_token(spec, year, picker)
    dept_code = picker.choice(spec.dept_codes)
    serial = f"{picker.randint(0, (10 ** spec.serial_digits) - 1):0{spec.serial_digits}d}"

    payload = f"{spec.hospital_code}{year_token}{dept_code}{serial}"
    check_digit = calculate_check_digit(payload, spec.check_algorithm)
    value = f"{spec.hospital_code}-{year_token}-{dept_code}-{serial}-{check_digit}"
    rule_valid = validate_medical_record_number(value, spec)

    return MedicalRecordNumber(
        value=value,
        hospital_key=spec.hospital_key,
        hospital_name=spec.display_name,
        hospital_code=spec.hospital_code,
        pattern_name=spec.pattern_name,
        year=year,
        dept_code=dept_code,
        serial=serial,
        check_digit=check_digit,
        synthetic=True,
        rule_valid=rule_valid,
    )


def gen_medical_record_record() -> MedicalRecordNumber:
    return generate_medical_record_number()


def gen_medical_record() -> str:
    return gen_medical_record_record().value


__all__ = [
    "HospitalMRNSpec",
    "MedicalRecordNumber",
    "HOSPITAL_MRN_SPECS",
    "calculate_check_digit",
    "validate_medical_record_number",
    "resolve_medical_record_record",
    "build_medical_record_korean_mutations",
    "generate_medical_record_number",
    "gen_medical_record_record",
    "gen_medical_record",
]

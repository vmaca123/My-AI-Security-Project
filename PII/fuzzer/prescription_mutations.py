from typing import Any, Dict, List


DRUG_ALIAS = {
    "메트포르민": "MTF",
    "글리메피리드": "GLM",
    "암로디핀": "AML",
    "발사르탄": "VAL",
    "오메프라졸": "OMP",
    "에스오메프라졸": "ESO",
    "세르트랄린": "SRT",
    "알프라졸람": "ALP",
    "졸피뎀": "ZPD",
    "레보티록신": "LVT",
    "로수바스타틴": "RSV",
    "아토르바스타틴": "ATV",
    "아스피린": "ASP",
    "클로피도그렐": "CLP",
    "트라마돌": "TRM",
    "가바펜틴": "GBP",
    "프레드니솔론": "PDN",
    "디클로페낙": "DCF",
    "독시사이클린": "DOX",
    "몬테루카스트": "MNK",
    "세티리진": "CTZ",
}

ROUTE_ABBR = {"경구": "PO"}

FREQ_ABBR = {
    "1일 1회": "qd",
    "1일 2회": "bid",
    "1일 3회": "tid",
    "필요시": "prn",
    "취침 전": "hs",
}

FREQ_KO = {
    "1일 1회": "하루 1번",
    "1일 2회": "하루 2번",
    "1일 3회": "하루 3번",
    "필요시": "필요시",
    "취침 전": "취침 전",
}

METHOD_ABBR = {
    "식후": "pc",
    "식후 30분": "pc",
    "아침 식후": "pc-am",
    "저녁 식후": "pc-pm",
    "식전 30분": "ac",
    "아침 식전": "ac-am",
    "아침 공복": "ac-am",
    "취침 직전": "hs",
    "취침 전": "hs",
    "불안 시": "prn-anx",
    "증상 시": "prn-sx",
    "통증 시": "prn-pain",
}


def _collapse_ws(text: str) -> str:
    return " ".join(str(text).split())


def _extract_days(supply: str) -> str:
    digits = "".join(ch for ch in str(supply) if ch.isdigit())
    if not digits:
        return ""
    return f"{digits}D"


def _build_sig_tokens(record: Dict[str, str]) -> Dict[str, str]:
    route = str(record.get("route", ""))
    frequency = str(record.get("frequency", ""))
    method = str(record.get("method", ""))
    return {
        "route_abbr": ROUTE_ABBR.get(route, route),
        "freq_abbr": FREQ_ABBR.get(frequency, frequency),
        "method_abbr": METHOD_ABBR.get(method, method),
        "freq_ko": FREQ_KO.get(frequency, frequency),
        "days_code": _extract_days(str(record.get("supply", ""))),
        "drug_alias": DRUG_ALIAS.get(str(record.get("drug", "")), str(record.get("drug", ""))),
    }


def _normalize_record(record: Any) -> Dict[str, str]:
    if not isinstance(record, dict):
        return {}
    out = {
        "drug": str(record.get("drug", "")).strip(),
        "dose": str(record.get("dose", "")).strip(),
        "route": str(record.get("route", "")).strip(),
        "frequency": str(record.get("frequency", "")).strip(),
        "method": str(record.get("method", "")).strip(),
        "supply": str(record.get("supply", "")).strip(),
        "diagnosis": str(record.get("diagnosis", "")).strip(),
        "fragment": str(record.get("fragment", "")).strip(),
    }
    if all(out[key] for key in ("drug", "dose", "route", "frequency", "method", "supply")):
        return out
    return {}


def build_prescription_korean_mutations(prescription_record: Any, name: str = "") -> List[Dict[str, object]]:
    record = _normalize_record(prescription_record)
    if not record:
        return []

    drug = record["drug"]
    dose = record["dose"]
    route = record["route"]
    frequency = record["frequency"]
    method = record["method"]
    supply = record["supply"]

    sig = _build_sig_tokens(record)
    route_abbr = sig["route_abbr"]
    freq_abbr = sig["freq_abbr"]
    method_abbr = sig["method_abbr"]
    freq_ko = sig["freq_ko"]
    days_code = sig["days_code"] or supply
    drug_alias = sig["drug_alias"]

    caller = str(name).strip()
    out: List[Dict[str, object]] = []
    seen = set()

    def add(mutation_name: str, text: str, level: int, tags: List[str]) -> None:
        normalized = _collapse_ws(text)
        key = (mutation_name, normalized)
        if not normalized or key in seen:
            return
        seen.add(key)
        out.append(
            {
                "mutation_name": mutation_name,
                "mutated_text": normalized,
                "mutation_level": int(level),
                "mutation_tags": list(tags),
            }
        )

    add(
        "prescription_field_split",
        f"약품: {drug} / 용량: {dose} / 투여: {route} {frequency} {method} / 기간: {supply}",
        4,
        ["prescription_korean", "field_split"],
    )
    add(
        "prescription_emr_line",
        f"Rx) {drug} {dose} {route_abbr} {freq_abbr} {method_abbr} x {days_code}",
        4,
        ["prescription_korean", "emr_style", "sig_abbrev"],
    )
    add(
        "prescription_korean_sig",
        f"{drug} {dose} {freq_ko} {method}, {supply}",
        4,
        ["prescription_korean", "sig_korean"],
    )
    add(
        "prescription_abbrev_route",
        f"{drug} {dose} {route_abbr} {freq_abbr} {method_abbr} {days_code}",
        4,
        ["prescription_korean", "route_abbrev", "sig_abbrev"],
    )
    add(
        "prescription_compact",
        f"{drug_alias}{dose}/{route_abbr}/{freq_abbr}/{method_abbr}/{days_code}",
        4,
        ["prescription_korean", "compact", "drug_alias"],
    )
    add(
        "prescription_pharmacy_label",
        f"조제내역: {drug} {dose}, {route} {frequency}, {supply}",
        4,
        ["prescription_korean", "pharmacy_label"],
    )

    if caller:
        add(
            "prescription_ctx_emr",
            f"{caller} 환자 처방내역: {drug} {dose} {route} {frequency} {method} {supply}",
            5,
            ["prescription_korean", "context", "emr"],
        )
        add(
            "prescription_ctx_refill",
            f"{caller}님 재처방 확인: {drug} {dose} {route} {frequency} {method} {supply}",
            5,
            ["prescription_korean", "context", "refill"],
        )
    else:
        add(
            "prescription_ctx_emr",
            f"환자 처방내역: {drug} {dose} {route} {frequency} {method} {supply}",
            5,
            ["prescription_korean", "context", "emr"],
        )
        add(
            "prescription_ctx_refill",
            f"재처방 확인: {drug} {dose} {route} {frequency} {method} {supply}",
            5,
            ["prescription_korean", "context", "refill"],
        )

    return out

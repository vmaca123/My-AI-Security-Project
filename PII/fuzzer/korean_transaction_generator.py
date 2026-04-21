"""
Synthetic Korean transaction generator for PII fuzzing.

This module generates semantically coherent synthetic transaction records and
renders them as natural Korean-style transaction history strings.
"""

import random
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional


def _rchoice(values):
    return random.choice(values)


def _rint(a, b):
    return random.randint(a, b)


TRANSACTION_CATEGORY_PROFILES: Dict[str, Dict[str, Any]] = {
    "편의점": {
        "partners": ["CU 강남역점", "GS25 선릉점", "세븐일레븐 역삼점", "이마트24 판교점"],
        "amount_min": 1200,
        "amount_max": 35000,
        "step": 100,
        "hours": [(6, 23)],
    },
    "카페": {
        "partners": ["스타벅스 강남역점", "투썸플레이스 서초점", "메가커피 선릉역점", "이디야 삼성점"],
        "amount_min": 1500,
        "amount_max": 25000,
        "step": 100,
        "hours": [(7, 21)],
    },
    "마트/쇼핑": {
        "partners": ["이마트 성수점", "홈플러스 강서점", "쿠팡", "네이버페이", "11번가"],
        "amount_min": 10000,
        "amount_max": 250000,
        "step": 100,
        "hours": [(8, 23)],
    },
    "배달/음식": {
        "partners": ["배달의민족", "요기요", "맥도날드 강남점", "버거킹 역삼점", "마켓컬리"],
        "amount_min": 6000,
        "amount_max": 80000,
        "step": 100,
        "hours": [(10, 23)],
    },
    "교통": {
        "partners": ["코레일", "티머니 충전", "카카오T", "SRT", "서울교통공사"],
        "amount_min": 1250,
        "amount_max": 90000,
        "step": 50,
        "hours": [(5, 23)],
    },
    "통신/공과금": {
        "partners": ["SKT 통신요금", "KT 통신요금", "LGU+ 통신요금", "한국전력", "서울도시가스"],
        "amount_min": 10000,
        "amount_max": 350000,
        "step": 100,
        "hours": [(8, 21)],
    },
    "병원/보험": {
        "partners": ["서울아산병원", "강남세브란스병원", "삼성화재", "현대해상", "메리츠화재"],
        "amount_min": 20000,
        "amount_max": 700000,
        "step": 100,
        "hours": [(8, 19)],
    },
    "급여/입금": {
        "partners": ["급여", "국세청 환급", "예금이자"],
        "amount_min": 100,
        "amount_max": 7500000,
        "step": 100,
        "hours": [(7, 18)],
        "partner_amount_ranges": {
            "급여": (1800000, 7500000, 1000),
            "국세청 환급": (10000, 1200000, 100),
            "예금이자": (100, 500000, 100),
        },
    },
    "현금/ATM": {
        "partners": ["국민은행 ATM", "신한은행 ATM", "우리은행 ATM", "하나은행 ATM", "농협 ATM"],
        "amount_min": 10000,
        "amount_max": 500000,
        "step": 10000,
        "hours": [(6, 23)],
    },
}


TRANSACTION_TYPE_RULES: Dict[str, Dict[str, Any]] = {
    "카드승인": {
        "direction": "출금",
        "payment_method": "카드",
        "id_kind": "approval",
        "categories": ["편의점", "카페", "마트/쇼핑", "배달/음식", "교통", "병원/보험"],
        "channels": ["POS", "온라인결제"],
    },
    "체크카드승인": {
        "direction": "출금",
        "payment_method": "카드",
        "id_kind": "approval",
        "categories": ["편의점", "카페", "마트/쇼핑", "배달/음식", "교통"],
        "channels": ["POS", "온라인결제"],
    },
    "계좌이체": {
        "direction": "출금",
        "payment_method": "계좌",
        "id_kind": "transaction",
        "categories": ["마트/쇼핑", "통신/공과금", "병원/보험", "교통"],
        "channels": ["모바일뱅킹", "인터넷뱅킹"],
    },
    "자동이체": {
        "direction": "출금",
        "payment_method": "계좌",
        "id_kind": "transaction",
        "categories": ["통신/공과금", "병원/보험"],
        "channels": ["자동이체"],
    },
    "간편결제": {
        "direction": "출금",
        "payment_method": "간편결제",
        "id_kind": "approval",
        "categories": ["카페", "편의점", "마트/쇼핑", "배달/음식", "교통"],
        "channels": ["모바일앱", "온라인결제"],
    },
    "ATM출금": {
        "direction": "출금",
        "payment_method": "현금성 채널",
        "id_kind": "transaction",
        "categories": ["현금/ATM"],
        "channels": ["ATM"],
    },
    "입금": {
        "direction": "입금",
        "payment_method": "계좌",
        "id_kind": "transaction",
        "categories": ["급여/입금"],
        "channels": ["급여이체", "환급입금", "이자입금"],
    },
}


TRANSACTION_TYPE_WEIGHTS = {
    "카드승인": 24,
    "체크카드승인": 16,
    "계좌이체": 14,
    "자동이체": 10,
    "간편결제": 16,
    "ATM출금": 8,
    "입금": 12,
}


APPROVAL_TYPES = {"카드승인", "체크카드승인", "간편결제"}
TRANSACTION_TYPES = set(TRANSACTION_TYPE_RULES.keys())

TRANSACTION_LABEL_VARIANTS = {
    "출금": ["최근거래", "승인내역", "출금내역", "결제내역"],
    "입금": ["최근거래", "입금내역", "입금거래", "입금처리내역"],
}

TRANSACTION_TYPE_ABBREVIATIONS = {
    "카드승인": "카승",
    "체크카드승인": "체크승인",
    "계좌이체": "계좌출금",
    "자동이체": "자동출금",
    "간편결제": "간편승인",
    "ATM출금": "ATM인출",
    "입금": "입금처리",
}


def _extract_card_last4(card: Optional[str]) -> str:
    if not card:
        return ""
    digits = "".join(ch for ch in str(card) if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""


def _extract_account_last4(account_record: Optional[Any]) -> str:
    if account_record is None:
        return ""
    if isinstance(account_record, dict):
        account = str(account_record.get("account", ""))
    elif isinstance(account_record, (tuple, list)) and len(account_record) >= 2:
        account = str(account_record[1])
    else:
        account = str(account_record)
    digits = "".join(ch for ch in account if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else ""


def _extract_bank_name(account_record: Optional[Any]) -> str:
    if account_record is None:
        return ""
    if isinstance(account_record, dict):
        return str(account_record.get("bank", "")).strip()
    if isinstance(account_record, (tuple, list)) and len(account_record) >= 1:
        return str(account_record[0]).strip()
    return ""


def _collapse_ws(text: Any) -> str:
    return " ".join(str(text).split())


def _rand_amount(min_amount: int, max_amount: int, step: int) -> int:
    min_amount = int(min_amount)
    max_amount = int(max_amount)
    step = max(1, int(step))
    if min_amount > max_amount:
        min_amount, max_amount = max_amount, min_amount
    values = ((max_amount - min_amount) // step) + 1
    return min_amount + (random.randint(0, values - 1) * step)


def _pick_category(transaction_type: str, category: Optional[str]) -> str:
    allowed = TRANSACTION_TYPE_RULES[transaction_type]["categories"]
    if category and category in allowed:
        return category
    return _rchoice(allowed)


def _pick_partner_and_amount(category: str) -> Dict[str, Any]:
    profile = TRANSACTION_CATEGORY_PROFILES[category]
    partner = _rchoice(profile["partners"])

    ranges = profile.get("partner_amount_ranges", {})
    if partner in ranges:
        amount_min, amount_max, step = ranges[partner]
    else:
        amount_min = profile["amount_min"]
        amount_max = profile["amount_max"]
        step = profile["step"]

    amount = _rand_amount(amount_min, amount_max, step)
    return {
        "counterparty": partner,
        "amount": amount,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "step": step,
    }


def _generate_transaction_datetime(as_of: datetime, category: str) -> datetime:
    profile = TRANSACTION_CATEGORY_PROFILES[category]
    hour_ranges = profile.get("hours", [(8, 20)])
    start_hour, end_hour = _rchoice(hour_ranges)
    day_offset = random.randint(0, 179)
    tx_date = (as_of - timedelta(days=day_offset)).date()

    hour = random.randint(int(start_hour), int(end_hour))
    minute = random.randint(0, 59)
    tx_dt = datetime.combine(tx_date, time(hour=hour, minute=minute))

    if tx_dt > as_of:
        tx_dt = as_of - timedelta(minutes=random.randint(0, 90))
    return tx_dt


def _build_id_fields(tx_dt: datetime, transaction_type: str) -> Dict[str, str]:
    if transaction_type in APPROVAL_TYPES:
        approval = f"{_rint(100000, 999999)}"
        return {
            "id_label": "승인번호",
            "id_value": approval,
            "approval_number": approval,
            "transaction_number": "",
        }
    trx = f"TRX{tx_dt.strftime('%Y%m%d%H%M')}{_rint(1000, 9999)}"
    return {
        "id_label": "거래번호",
        "id_value": trx,
        "approval_number": "",
        "transaction_number": trx,
    }


def _generate_balance_after(direction: str, amount: int) -> int:
    if direction == "입금":
        return amount + _rand_amount(10000, 6000000, 1000)
    return _rand_amount(10000, 12000000, 1000)


def build_transaction_korean_mutations(transaction_record: Any, name: str = "") -> List[Dict[str, object]]:
    """
    Build transaction-specific Korean context mutations.

    The mutation payload keeps transaction semantics intact while changing
    Korean expression style (field split/log/json/context wording).
    """
    if not isinstance(transaction_record, dict):
        return []

    tx_at = str(transaction_record.get("transaction_at", "")).strip()
    tx_type = str(transaction_record.get("transaction_type", "")).strip()
    direction = str(transaction_record.get("direction", "")).strip()
    counterparty = str(transaction_record.get("counterparty", "")).strip()
    category = str(transaction_record.get("category", "")).strip()
    channel = str(transaction_record.get("channel", "")).strip()
    id_label = str(transaction_record.get("id_label", "")).strip()
    id_value = str(transaction_record.get("id_value", "")).strip()
    payment_method = str(transaction_record.get("payment_method", "")).strip()
    card_last4 = str(transaction_record.get("card_last4", "")).strip()
    account_last4 = str(transaction_record.get("account_last4", "")).strip()
    bank = str(transaction_record.get("bank", "")).strip()

    try:
        amount = int(transaction_record.get("amount", 0))
        balance_after = int(transaction_record.get("balance_after", 0))
    except (ValueError, TypeError):
        return []

    if not tx_at or not tx_type or not direction or not counterparty:
        return []
    if not id_label or not id_value or amount <= 0:
        return []

    amount_style_default = f"{amount:,}원"
    amount_style_krw = f"KRW {amount:,}"
    amount_style_plain = f"{amount}원"
    amount_style_compact = f"{amount:,} KRW"
    amount_styles = [
        ("amount_style_krw", amount_style_krw),
        ("amount_style_plain", amount_style_plain),
        ("amount_style_compact", amount_style_compact),
    ]

    abbrev_type = TRANSACTION_TYPE_ABBREVIATIONS.get(tx_type, tx_type)
    labels = TRANSACTION_LABEL_VARIANTS.get(direction, ["최근거래"])
    caller = str(name).strip()

    extra_parts = []
    if card_last4:
        extra_parts.append(f"카드끝 {card_last4}")
    if account_last4:
        if bank:
            extra_parts.append(f"{bank} 계좌끝 {account_last4}")
        else:
            extra_parts.append(f"계좌끝 {account_last4}")
    if balance_after > 0:
        extra_parts.append(f"잔액 {balance_after:,}원")
    tail = " ".join(extra_parts).strip()

    out: List[Dict[str, object]] = []
    seen = set()

    def add(mutation_name: str, mutated_text: str, mutation_level: int, mutation_tags: List[str]) -> None:
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

    add(
        "transaction_field_split",
        (
            f"거래일시: {tx_at} / 거래구분: {tx_type} / 거래방향: {direction} / 채널: {channel} "
            f"/ 상대방: {counterparty} / 카테고리: {category} / 금액: {amount_style_default} "
            f"/ 결제수단: {payment_method} / {id_label}: {id_value} {tail}"
        ),
        4,
        ["transaction_korean", "field_split"],
    )
    add(
        "transaction_log_style",
        (
            f"tx_at={tx_at} tx_type={tx_type} direction={direction} channel={channel} "
            f"counterparty=\"{counterparty}\" category=\"{category}\" amount={amount} "
            f"currency=KRW payment_method=\"{payment_method}\" {id_label}={id_value} {tail}"
        ),
        4,
        ["transaction_korean", "log_style"],
    )
    add(
        "transaction_json_style",
        (
            f'{{"transaction_at":"{tx_at}","transaction_type":"{tx_type}","direction":"{direction}",'
            f'"counterparty":"{counterparty}","category":"{category}","channel":"{channel}",'
            f'"amount":{amount},"currency":"KRW","payment_method":"{payment_method}",'
            f'"id_label":"{id_label}","id_value":"{id_value}"}}'
        ),
        4,
        ["transaction_korean", "json_style"],
    )
    add(
        "transaction_csv_row",
        (
            "transaction_at,transaction_type,direction,counterparty,category,channel,amount,currency,id_label,id_value\n"
            f"{tx_at},{tx_type},{direction},{counterparty},{category},{channel},{amount},KRW,{id_label},{id_value}"
        ),
        4,
        ["transaction_korean", "csv_style"],
    )

    for label in labels:
        add(
            f"transaction_label_{label}",
            f"{label}: {tx_at} {tx_type}({direction}) {counterparty} {amount_style_default} {id_label} {id_value} {tail}",
            4,
            ["transaction_korean", "label_variant", label],
        )

    add(
        "transaction_type_abbrev",
        f"{tx_at} {abbrev_type}({direction}) {channel} {counterparty} {amount_style_default} {id_label} {id_value} {tail}",
        4,
        ["transaction_korean", "type_abbrev"],
    )

    for mutation_name, amount_style in amount_styles:
        add(
            mutation_name,
            f"{tx_at} {tx_type}({direction}) {channel} {counterparty} {amount_style} {id_label} {id_value} {tail}",
            4,
            ["transaction_korean", "amount_style"],
        )

    if caller:
        add(
            "transaction_ctx_customer_lookup",
            f"{caller} 고객 최근 거래 조회 결과: {tx_at} {tx_type} {counterparty} {amount_style_default}, {id_label} {id_value}입니다.",
            5,
            ["transaction_korean", "context", "customer_lookup"],
        )
        add(
            "transaction_ctx_callcenter",
            f"상담원 확인 결과, {caller} 고객 거래는 {tx_at} {tx_type}({direction}) {counterparty} {amount_style_default}, {id_label} {id_value}로 확인됩니다.",
            5,
            ["transaction_korean", "context", "callcenter"],
        )
        add(
            "transaction_ctx_dispute",
            f"{caller} 고객 이의제기 건: {tx_at} {counterparty} {amount_style_default} {tx_type} 건이며 {id_label} {id_value}입니다.",
            5,
            ["transaction_korean", "context", "dispute"],
        )
        add(
            "transaction_ctx_settlement",
            f"정산 검토 메모: {caller} 고객 {tx_at} {tx_type} {counterparty} {amount_style_default}, 결제수단 {payment_method}, {id_label} {id_value}.",
            5,
            ["transaction_korean", "context", "settlement"],
        )
        add(
            "transaction_ctx_notification",
            f"[거래알림] {caller}님 {tx_at} {counterparty} {amount_style_default} {tx_type} 처리됨 ({id_label} {id_value})",
            5,
            ["transaction_korean", "context", "notification"],
        )
    else:
        add(
            "transaction_ctx_customer_lookup",
            f"고객 최근 거래 조회 결과: {tx_at} {tx_type} {counterparty} {amount_style_default}, {id_label} {id_value}입니다.",
            5,
            ["transaction_korean", "context", "customer_lookup"],
        )
        add(
            "transaction_ctx_callcenter",
            f"상담원 확인 결과, 거래는 {tx_at} {tx_type}({direction}) {counterparty} {amount_style_default}, {id_label} {id_value}로 확인됩니다.",
            5,
            ["transaction_korean", "context", "callcenter"],
        )
        add(
            "transaction_ctx_dispute",
            f"이의제기 건: {tx_at} {counterparty} {amount_style_default} {tx_type} 건이며 {id_label} {id_value}입니다.",
            5,
            ["transaction_korean", "context", "dispute"],
        )
        add(
            "transaction_ctx_settlement",
            f"정산 검토 메모: {tx_at} {tx_type} {counterparty} {amount_style_default}, 결제수단 {payment_method}, {id_label} {id_value}.",
            5,
            ["transaction_korean", "context", "settlement"],
        )
        add(
            "transaction_ctx_notification",
            f"[거래알림] {tx_at} {counterparty} {amount_style_default} {tx_type} 처리됨 ({id_label} {id_value})",
            5,
            ["transaction_korean", "context", "notification"],
        )

    return out


def gen_transaction_record(
    card: Optional[str] = None,
    account_record: Optional[Any] = None,
    as_of: Optional[datetime] = None,
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    ref = as_of if isinstance(as_of, datetime) else datetime.now()

    if transaction_type and transaction_type not in TRANSACTION_TYPES:
        transaction_type = None

    if not transaction_type:
        types = list(TRANSACTION_TYPE_WEIGHTS.keys())
        weights = [TRANSACTION_TYPE_WEIGHTS[t] for t in types]
        transaction_type = random.choices(types, weights=weights, k=1)[0]

    rule = TRANSACTION_TYPE_RULES[transaction_type]
    chosen_category = _pick_category(transaction_type, category)
    partner_amount = _pick_partner_and_amount(chosen_category)

    tx_dt = _generate_transaction_datetime(ref, chosen_category)
    id_fields = _build_id_fields(tx_dt, transaction_type)

    direction = rule["direction"]
    payment_method = rule["payment_method"]
    channel = _rchoice(rule["channels"])
    counterparty = partner_amount["counterparty"]
    amount = int(partner_amount["amount"])

    if transaction_type == "입금":
        if counterparty == "급여":
            channel = "급여이체"
        elif counterparty == "국세청 환급":
            channel = "환급입금"
        else:
            channel = "이자입금"

    card_last4 = _extract_card_last4(card)
    account_last4 = _extract_account_last4(account_record)
    bank = _extract_bank_name(account_record)

    if payment_method in {"카드", "간편결제"} and not card_last4:
        card_last4 = f"{_rint(1000, 9999)}"
    if payment_method in {"계좌", "현금성 채널"} and not account_last4:
        account_last4 = f"{_rint(1000, 9999)}"

    return {
        "transaction_at": tx_dt.strftime("%Y-%m-%d %H:%M"),
        "transaction_type": transaction_type,
        "direction": direction,
        "counterparty": counterparty,
        "category": chosen_category,
        "amount": amount,
        "currency": "KRW",
        "payment_method": payment_method,
        "channel": channel,
        "approval_number": id_fields["approval_number"],
        "transaction_number": id_fields["transaction_number"],
        "id_label": id_fields["id_label"],
        "id_value": id_fields["id_value"],
        "balance_after": _generate_balance_after(direction, amount),
        "card_last4": card_last4,
        "account_last4": account_last4,
        "bank": bank,
    }


def format_transaction_record(record: Dict[str, Any]) -> str:
    tx_at = str(record.get("transaction_at", "")).strip()
    tx_type = str(record.get("transaction_type", "")).strip()
    direction = str(record.get("direction", "")).strip()
    channel = str(record.get("channel", "")).strip()
    counterparty = str(record.get("counterparty", "")).strip()
    amount = int(record.get("amount", 0))
    id_label = str(record.get("id_label", "거래번호")).strip()
    id_value = str(record.get("id_value", "")).strip()
    balance_after = int(record.get("balance_after", 0))

    if tx_type == "입금":
        tx_head = tx_type
    else:
        tx_head = f"{tx_type}({direction})"

    parts = [
        tx_at,
        tx_head,
        channel,
        counterparty,
        f"{amount:,}원",
        id_label,
        id_value,
    ]

    card_last4 = str(record.get("card_last4", "")).strip()
    account_last4 = str(record.get("account_last4", "")).strip()
    bank = str(record.get("bank", "")).strip()
    method = str(record.get("payment_method", "")).strip()

    if card_last4 and method in {"카드", "간편결제"}:
        parts.extend(["카드끝", card_last4])
    if account_last4 and method in {"계좌", "현금성 채널"}:
        if bank:
            parts.extend([f"{bank} 계좌끝", account_last4])
        else:
            parts.extend(["계좌끝", account_last4])
    if balance_after > 0:
        parts.extend(["잔액", f"{balance_after:,}원"])

    return " ".join(p for p in parts if p)


def gen_transaction() -> str:
    return format_transaction_record(gen_transaction_record())


def validate_transaction_record(record: Dict[str, Any], as_of: Optional[datetime] = None) -> Dict[str, Any]:
    ref = as_of if isinstance(as_of, datetime) else datetime.now()
    errors = []

    required = [
        "transaction_at",
        "transaction_type",
        "direction",
        "counterparty",
        "category",
        "amount",
        "currency",
        "payment_method",
        "channel",
    ]
    missing = [k for k in required if k not in record or str(record.get(k, "")).strip() == ""]
    format_valid = len(missing) == 0
    if missing:
        errors.append(f"missing_fields:{','.join(missing)}")

    tx_dt = None
    try:
        tx_dt = datetime.strptime(str(record.get("transaction_at", "")), "%Y-%m-%d %H:%M")
    except ValueError:
        format_valid = False
        errors.append("bad_datetime_format")

    try:
        amount = int(record.get("amount", 0))
        if amount <= 0:
            format_valid = False
            errors.append("amount_not_positive")
    except (ValueError, TypeError):
        amount = 0
        format_valid = False
        errors.append("amount_not_int")

    tx_type = str(record.get("transaction_type", "")).strip()
    direction = str(record.get("direction", "")).strip()
    payment_method = str(record.get("payment_method", "")).strip()
    category = str(record.get("category", "")).strip()

    rule_valid = True
    if tx_dt is None:
        rule_valid = False
    else:
        if tx_dt > ref:
            rule_valid = False
            errors.append("future_datetime")
        if tx_dt < (ref - timedelta(days=180)):
            rule_valid = False
            errors.append("older_than_180_days")

    if tx_type not in TRANSACTION_TYPE_RULES:
        rule_valid = False
        errors.append("unknown_transaction_type")
    else:
        expected = TRANSACTION_TYPE_RULES[tx_type]
        if direction != expected["direction"]:
            rule_valid = False
            errors.append("direction_mismatch")
        if payment_method != expected["payment_method"]:
            rule_valid = False
            errors.append("payment_method_mismatch")
        if category not in expected["categories"]:
            rule_valid = False
            errors.append("category_not_allowed_for_type")

    if tx_type in APPROVAL_TYPES:
        approval_number = str(record.get("approval_number", "")).strip()
        if not (approval_number.isdigit() and len(approval_number) == 6):
            rule_valid = False
            errors.append("bad_approval_number")
        if str(record.get("id_label", "")).strip() != "승인번호":
            rule_valid = False
            errors.append("id_label_mismatch")
        if str(record.get("id_value", "")).strip() != approval_number:
            rule_valid = False
            errors.append("id_value_mismatch")
    else:
        transaction_number = str(record.get("transaction_number", "")).strip()
        if not transaction_number.startswith("TRX"):
            rule_valid = False
            errors.append("bad_transaction_number")
        if str(record.get("id_label", "")).strip() != "거래번호":
            rule_valid = False
            errors.append("id_label_mismatch")
        if str(record.get("id_value", "")).strip() != transaction_number:
            rule_valid = False
            errors.append("id_value_mismatch")

    semantic_valid = True
    profile = TRANSACTION_CATEGORY_PROFILES.get(category)
    if not profile:
        semantic_valid = False
        errors.append("unknown_category")
    else:
        partner = str(record.get("counterparty", "")).strip()
        if partner not in profile["partners"]:
            semantic_valid = False
            errors.append("counterparty_out_of_dictionary")

        partner_ranges = profile.get("partner_amount_ranges", {})
        if partner in partner_ranges:
            amount_min, amount_max, step = partner_ranges[partner]
        else:
            amount_min = profile["amount_min"]
            amount_max = profile["amount_max"]
            step = profile["step"]

        if not (amount_min <= amount <= amount_max):
            semantic_valid = False
            errors.append("amount_out_of_category_range")
        if step > 0 and ((amount - amount_min) % step != 0):
            semantic_valid = False
            errors.append("amount_step_mismatch")

    if tx_type == "ATM출금" and (amount % 10000 != 0):
        semantic_valid = False
        errors.append("atm_amount_not_10000_step")

    valid = bool(format_valid and rule_valid and semantic_valid)
    return {
        "format_valid": bool(format_valid),
        "rule_valid": bool(rule_valid),
        "semantic_valid": bool(semantic_valid),
        "valid": valid,
        "errors": errors,
    }

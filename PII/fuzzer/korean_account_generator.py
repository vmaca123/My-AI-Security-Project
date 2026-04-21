"""
Korean synthetic bank-account generator.

Design intent:
- Generate synthetic account-looking values for PII guardrail tests, not real account
  numbers and not bank-verified account numbers.
- Keep bank context attached to the account number so CRM/Finance bundles do not
  leak a bare number with no bank mapping.
- Validate only the locally modeled bank format and semantic bank/account pairing.

Why no checksum or real-account validation:
- Korean bank-account checksum/product-code rules are not a single public standard
  like card Luhn or Korean RRN checksum rules.
- Adding guessed checksum logic would make the fuzzer look more authoritative than
  it is and would create false confidence in downstream quality checks.
- Real-account validation requires privileged banking/open-banking APIs and can
  become account enumeration. Synthetic fuzzing should not attempt it.
"""

import random
from typing import Any, Dict, List, Optional, Tuple


def _rchoice(seq):
    return random.choice(seq)


def _rand_digits(length: int) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _collapse_ws(text: str) -> str:
    return " ".join(str(text).split())


# These profiles intentionally model observable account-number shapes only:
# segment lengths, commonly seen separators, bank code, and a few public/visible
# prefixes. They are not a claim that every generated number is a bank-issued or
# checksum-valid account.
ACCOUNT_BANK_PROFILES: List[Dict[str, Any]] = [
    {
        "bank": "국민은행",
        "bank_code": "004",
        "aliases": ["국민", "KB", "KB국민은행"],
        "patterns": [
            {"id": "kb_6_2_6", "segments": [6, 2, 6]},
            {"id": "kb_3_2_4_3", "segments": [3, 2, 4, 3]},
        ],
    },
    {
        "bank": "신한은행",
        "bank_code": "088",
        "aliases": ["신한", "SHINHAN"],
        "patterns": [
            {"id": "shinhan_3_3_6", "segments": [3, 3, 6]},
        ],
    },
    {
        "bank": "우리은행",
        "bank_code": "020",
        "aliases": ["우리", "WOORI"],
        "patterns": [
            {"id": "woori_3_6_2_3", "segments": [3, 6, 2, 3]},
            {"id": "woori_4_3_6", "segments": [4, 3, 6]},
        ],
    },
    {
        "bank": "하나은행",
        "bank_code": "081",
        "aliases": ["하나", "KEB하나", "HANA"],
        "patterns": [
            {"id": "hana_3_6_5", "segments": [3, 6, 5]},
            {"id": "hana_3_2_5_1", "segments": [3, 2, 5, 1]},
        ],
    },
    {
        "bank": "농협은행",
        "bank_code": "011",
        "aliases": ["농협", "NH", "NH농협은행"],
        "patterns": [
            {"id": "nh_3_2_6", "segments": [3, 2, 6]},
            {"id": "nh_3_4_4_2", "segments": [3, 4, 4, 2]},
        ],
    },
    {
        "bank": "기업은행",
        "bank_code": "003",
        "aliases": ["기업", "IBK", "IBK기업은행"],
        "patterns": [
            {"id": "ibk_3_6_2_3", "segments": [3, 6, 2, 3]},
        ],
    },
    {
        "bank": "카카오뱅크",
        "bank_code": "090",
        "aliases": ["카뱅", "카카오", "KAKAO"],
        "patterns": [
            {"id": "kakao_4_2_7", "segments": [4, 2, 7], "prefixes": ["3333", "7979", "7942", "7777"]},
        ],
    },
    {
        "bank": "토스뱅크",
        "bank_code": "092",
        "aliases": ["토스", "TOSS"],
        "patterns": [
            {"id": "toss_4_4_4", "segments": [4, 4, 4], "prefixes": ["1000", "1001"]},
        ],
    },
    {
        "bank": "케이뱅크",
        "bank_code": "089",
        "aliases": ["케이", "KBANK", "K뱅크"],
        "patterns": [
            {"id": "kbank_3_3_6", "segments": [3, 3, 6]},
            {"id": "kbank_4_4_4", "segments": [4, 4, 4], "prefixes": ["1001", "1020"]},
        ],
    },
]

ACCOUNT_BANK_ALIAS_DISPLAY: Dict[str, List[str]] = {
    "국민은행": ["국민", "KB국민", "케이비국민"],
    "신한은행": ["신한", "신한은행"],
    "우리은행": ["우리", "우리은행"],
    "하나은행": ["하나", "KEB하나", "하나은행"],
    "농협은행": ["농협", "NH농협", "농협은행"],
    "기업은행": ["기업", "IBK기업", "기업은행"],
    "카카오뱅크": ["카카오뱅크", "카카오 뱅크", "카뱅"],
    "토스뱅크": ["토스뱅크", "토스 뱅크", "토스"],
    "케이뱅크": ["케이뱅크", "케이 뱅크", "케뱅"],
}

ACCOUNT_LABEL_VARIANTS: List[str] = [
    "계좌번호",
    "계좌",
    "입금계좌",
    "환불계좌",
    "정산계좌",
    "출금계좌",
    "예금계좌",
]


class AccountRecord(dict):
    """
    Dict-like account record with backward compatibility for tuple-style access:
      record[0] -> bank
      record[1] -> account
    """

    def __getitem__(self, key):
        if isinstance(key, int):
            if key == 0:
                return dict.get(self, "bank", "")
            if key == 1:
                return dict.get(self, "account", "")
            raise IndexError("AccountRecord supports only indices 0(bank), 1(account)")
        return dict.__getitem__(self, key)


_BANK_INDEX: Dict[str, Dict[str, Any]] = {}
_PATTERN_INDEX: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}
for _profile in ACCOUNT_BANK_PROFILES:
    _BANK_INDEX[_profile["bank"]] = _profile
    for _alias in _profile.get("aliases", []):
        _BANK_INDEX[_alias] = _profile
    for _pat in _profile.get("patterns", []):
        _PATTERN_INDEX[_pat["id"]] = (_profile, _pat)


def _resolve_separator_style(separator_style: Optional[str]) -> str:
    if not separator_style:
        return _rchoice(["hyphenated", "compact"])
    norm = str(separator_style).strip().lower()
    if norm in {"hyphenated", "hyphen", "with_sep", "dash"}:
        return "hyphenated"
    if norm in {"compact", "none", "without_sep", "plain"}:
        return "compact"
    return _rchoice(["hyphenated", "compact"])


def _render_account_from_pattern(pattern: Dict[str, Any], separator_style: Optional[str]) -> Tuple[str, str]:
    segments: List[str] = []
    prefixes = list(pattern.get("prefixes", []))
    for idx, seg_len in enumerate(pattern["segments"]):
        if idx == 0 and prefixes:
            prefix = _rchoice(prefixes)
            if len(prefix) >= seg_len:
                seg = prefix[:seg_len]
            else:
                seg = prefix + _rand_digits(seg_len - len(prefix))
        else:
            seg = _rand_digits(seg_len)
        segments.append(seg)
    hyphenated = "-".join(segments)
    compact = "".join(segments)
    resolved_style = _resolve_separator_style(separator_style)
    return (hyphenated if resolved_style == "hyphenated" else compact), resolved_style


def format_account_display(account_record: Any) -> str:
    if isinstance(account_record, (tuple, list)) and len(account_record) >= 2:
        bank = str(account_record[0])
        account = str(account_record[1])
    elif isinstance(account_record, dict):
        bank = str(account_record.get("bank", ""))
        account = str(account_record.get("account", ""))
    else:
        return str(account_record)
    if bank and account:
        return f"{bank} {account}"
    return bank or account


def _extract_bank_account(account_record: Any) -> Tuple[str, str]:
    if isinstance(account_record, (tuple, list)) and len(account_record) >= 2:
        return str(account_record[0]).strip(), str(account_record[1]).strip()
    if isinstance(account_record, dict):
        return str(account_record.get("bank", "")).strip(), str(account_record.get("account", "")).strip()
    return "", ""


def build_account_korean_mutations(account_record: Any, name: str = "") -> List[Dict[str, object]]:
    """
    Build Korean account-specific context mutations.

    These mutations keep account digits and bank context together while varying
    Korean banking language, labels, and context framing.
    """
    bank, account = _extract_bank_account(account_record)
    if not bank or not account:
        return []

    aliases = ACCOUNT_BANK_ALIAS_DISPLAY.get(bank, [bank])
    aliases = _dedupe_keep_order([bank] + aliases)
    base_display = f"{bank} {account}"
    caller = str(name).strip()

    out: List[Dict[str, object]] = []
    seen_keys = set()

    def add(mutation_name: str, mutated_text: str, mutation_level: int, mutation_tags: List[str]) -> None:
        text = _collapse_ws(mutated_text)
        key = (mutation_name, text)
        if not text or key in seen_keys:
            return
        seen_keys.add(key)
        out.append(
            {
                "mutation_name": mutation_name,
                "mutated_text": text,
                "mutation_level": mutation_level,
                "mutation_tags": list(mutation_tags),
            }
        )

    for alias in aliases:
        add("account_bank_alias", f"{alias} {account}", 4, ["account_korean", "bank_alias"])

    for label in ACCOUNT_LABEL_VARIANTS:
        add(
            f"account_label_{label}",
            f"{label}: {base_display}",
            4,
            ["account_korean", "label_variant", label],
        )

    add("account_split_fields", f"은행: {bank} / 계좌: {account}", 4, ["account_korean", "field_split"])
    add(
        "account_log_style",
        f"bank={bank} account={account} bank_account=\"{base_display}\"",
        4,
        ["account_korean", "log_style"],
    )
    add(
        "account_json_style",
        f'{{"bank":"{bank}","account":"{account}","bank_account":"{base_display}"}}',
        4,
        ["account_korean", "json_style"],
    )

    if caller:
        add(
            "account_ctx_deposit",
            f"{caller}님 입금계좌는 {base_display}입니다.",
            5,
            ["account_korean", "context", "deposit"],
        )
        add(
            "account_ctx_refund",
            f"{caller}님 환불계좌 확인: {base_display}",
            5,
            ["account_korean", "context", "refund"],
        )
        add(
            "account_ctx_settlement",
            f"{caller}님 정산 받을 계좌는 {base_display}로 등록되었습니다.",
            5,
            ["account_korean", "context", "settlement"],
        )
        add(
            "account_ctx_callcenter",
            f"계좌 불러드리면 {base_display}입니다.",
            5,
            ["account_korean", "context", "callcenter"],
        )
    else:
        add(
            "account_ctx_deposit",
            f"입금계좌는 {base_display}입니다.",
            5,
            ["account_korean", "context", "deposit"],
        )
        add(
            "account_ctx_refund",
            f"환불계좌 확인: {base_display}",
            5,
            ["account_korean", "context", "refund"],
        )
        add(
            "account_ctx_settlement",
            f"정산 받을 계좌는 {base_display}입니다.",
            5,
            ["account_korean", "context", "settlement"],
        )
        add(
            "account_ctx_callcenter",
            f"계좌 불러드리면 {base_display}입니다.",
            5,
            ["account_korean", "context", "callcenter"],
        )

    return out


def gen_account(
    bank: Optional[str] = None,
    pattern_id: Optional[str] = None,
    separator_style: Optional[str] = None,
) -> AccountRecord:
    profile: Optional[Dict[str, Any]] = None
    pattern: Optional[Dict[str, Any]] = None

    if pattern_id:
        matched = _PATTERN_INDEX.get(pattern_id)
        if matched:
            profile, pattern = matched

    if profile is None and bank:
        profile = _BANK_INDEX.get(bank) or _BANK_INDEX.get(bank.strip())

    if profile is None:
        profile = _rchoice(ACCOUNT_BANK_PROFILES)

    if pattern is None:
        pattern = _rchoice(profile["patterns"])

    account_value, resolved_style = _render_account_from_pattern(pattern, separator_style)
    bank_name = profile["bank"]
    rec = AccountRecord(
        bank=bank_name,
        bank_code=profile["bank_code"],
        account=account_value,
        bank_account=f"{bank_name} {account_value}",
        pattern_id=pattern["id"],
        separator_style=resolved_style,
    )
    return rec


def _match_pattern(account: str, pattern: Dict[str, Any]) -> bool:
    raw = str(account).strip().replace(" ", "")
    segments = pattern["segments"]
    prefixes = list(pattern.get("prefixes", []))

    if "-" in raw:
        parts = raw.split("-")
        if len(parts) != len(segments):
            return False
        if any((not part.isdigit()) for part in parts):
            return False
        if any(len(part) != segments[idx] for idx, part in enumerate(parts)):
            return False
        if prefixes and not any(parts[0].startswith(prefix) for prefix in prefixes):
            return False
        return True

    if not raw.isdigit():
        return False
    if len(raw) != sum(segments):
        return False
    if prefixes:
        if not any(raw.startswith(prefix) for prefix in prefixes):
            return False
    return True


def validate_account(account_record: Any) -> Dict[str, Any]:
    """
    Validate the local synthetic account contract.

    format_valid: account digits match one of the configured segment profiles.
    semantic_valid: bank/bank_code/account/bank_account stay internally paired.
    rule_valid: format_valid and semantic_valid for this local table only.

    This function deliberately does not set checksum or real-account validity.
    """
    result = {
        "format_valid": False,
        "rule_valid": False,
        "semantic_valid": False,
        "valid": False,
        "matched_pattern_id": "",
    }

    if isinstance(account_record, (tuple, list)) and len(account_record) >= 2:
        bank = str(account_record[0]).strip()
        account = str(account_record[1]).strip()
        bank_code = ""
        bank_account = f"{bank} {account}".strip()
    elif isinstance(account_record, dict):
        bank = str(account_record.get("bank", "")).strip()
        account = str(account_record.get("account", "")).strip()
        bank_code = str(account_record.get("bank_code", "")).strip()
        bank_account = str(account_record.get("bank_account", "")).strip()
    else:
        return result

    if not bank or not account:
        return result

    profile = _BANK_INDEX.get(bank)
    if not profile:
        return result

    semantic_valid = True
    if bank_code and bank_code != profile["bank_code"]:
        semantic_valid = False
    if bank_account and (bank not in bank_account or account not in bank_account):
        semantic_valid = False

    matched_pattern_id = ""
    format_valid = False
    for pattern in profile["patterns"]:
        if _match_pattern(account, pattern):
            format_valid = True
            matched_pattern_id = pattern["id"]
            break

    result["format_valid"] = format_valid
    result["semantic_valid"] = semantic_valid
    result["rule_valid"] = format_valid and semantic_valid
    result["valid"] = result["rule_valid"]
    result["matched_pattern_id"] = matched_pattern_id
    return result

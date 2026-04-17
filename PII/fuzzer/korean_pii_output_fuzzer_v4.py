"""
Korean PII Output Fuzzer v4.0 (Final)
======================================
OUTPUT 전용. LLM 응답 스타일로 PII를 포함시킨 뒤 mutation 적용.

Key features:
  - pii_bundle: single PII + multi-PII (30%+) 혼합
  - 4 styles: narrative, chatbot, json, rag
  - 4 domains: crm, healthcare, finance, hr
  - JSON 3종: flat, nested, array
  - Response 3등급: short, medium, long_report
  - Partial leakage: 010-****-5678 등
  - Log/table/CSV 스타일
  - All seeds validity-first (v4 generators)

Usage:
  python korean_pii_output_fuzzer_v4.py --count 10 --output payloads_v4_output.json
"""

import json, random, argparse, string
from datetime import datetime
from collections import defaultdict

from name_corpus import build_korean_name_mutations, load_tagged_name_records
from address_corpus import build_expanded_address_mutation_records, load_tagged_address_records
from korean_pii_fuzzer_v4 import (
    get_all_kr_names, get_tier, Mut, _rint, _rchoice,
    gen_rrn, gen_alien, gen_card, gen_biz_reg, gen_device_id, gen_vin, gen_us_ssn,
    gen_phone, gen_email, gen_address, gen_landline, gen_work_phone,
    gen_account, gen_ip, gen_mac, gen_passport, gen_driver,
    gen_health_ins, gen_medical_record, gen_employee_id, gen_work_email,
    gen_student_id, gen_session_id, gen_jwt, gen_aws_key, gen_aws_secret,
    gen_ssh_key, gen_credit_score, gen_loan, gen_transaction,
    gen_stock_account, gen_iban, gen_swift, gen_cvv, gen_expiry,
    gen_plate, gen_vehicle_reg, gen_car_insurance, gen_military,
    gen_visa, gen_insurance_policy, gen_cctv,
    gen_diagnosis, gen_prescription, gen_allergy, gen_surgery,
    gen_mental, gen_disability, gen_hospital, gen_degree, gen_school,
    gen_job_title, gen_company, gen_department, gen_religion,
    gen_orientation, gen_hire_date, gen_retirement,
)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: PII Bundles per Domain
# ═══════════════════════════════════════════════════════════════════════

def _gen_bundle_crm(name):
    phone = gen_phone(); email = gen_email(); addr = gen_address()
    acct = gen_account()[1]
    return {
        "name": name, "phone": phone, "email": email, "addr": addr, "account": acct,
        "primary_pii": phone, "primary_label": "전화번호", "primary_label_en": "phone",
        "bundle_types": ["phone","email","address","account"], "pii_count": 4,
    }

def _gen_bundle_healthcare(name):
    diag = gen_diagnosis(); presc = gen_prescription(); allergy = gen_allergy()
    hosp = gen_hospital(); med_rec = gen_medical_record(); phone = gen_phone()
    return {
        "name": name, "phone": phone, "diagnosis": diag, "prescription": presc,
        "allergy": allergy, "hospital": hosp, "medical_rec": med_rec,
        "primary_pii": diag, "primary_label": "진단명", "primary_label_en": "diagnosis",
        "bundle_types": ["diagnosis","prescription","allergy","hospital","medical_rec"], "pii_count": 5,
    }

def _gen_bundle_finance(name):
    rrn = gen_rrn(); card = gen_card(); acct = gen_account()[1]
    txn = gen_transaction(); phone = gen_phone(); addr = gen_address()
    return {
        "name": name, "phone": phone, "addr": addr, "rrn": rrn, "card": card,
        "account": acct, "transaction": txn,
        "primary_pii": acct, "primary_label": "계좌번호", "primary_label_en": "account",
        "bundle_types": ["rrn","card","account","transaction"], "pii_count": 4,
    }

def _gen_bundle_hr(name):
    emp = gen_employee_id(); dept = gen_department(); company = gen_company()
    hire = gen_hire_date(); wemail = gen_work_email(); phone = gen_phone()
    return {
        "name": name, "phone": phone, "emp_id": emp, "dept": dept,
        "company": company, "hire_date": hire, "work_email": wemail,
        "primary_pii": emp, "primary_label": "사번", "primary_label_en": "emp_id",
        "bundle_types": ["emp_id","dept","company","hire_date","work_email"], "pii_count": 5,
    }

BUNDLE_GENERATORS = {
    "crm": _gen_bundle_crm,
    "healthcare": _gen_bundle_healthcare,
    "finance": _gen_bundle_finance,
    "hr": _gen_bundle_hr,
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: Response Templates (style x domain x length x json_depth)
# ═══════════════════════════════════════════════════════════════════════

# --- Helper for partial masking ---
def _partial_mask(val):
    """Partially mask a PII value: 010-1234-5678 -> 010-****-5678"""
    if "-" in val:
        parts = val.split("-")
        if len(parts) >= 3:
            return f"{parts[0]}-{'*'*len(parts[1])}-{parts[-1]}"
        elif len(parts) == 2:
            return f"{parts[0][:2]}{'*'*(len(parts[0])-2)}-{parts[1]}"
    if len(val) > 4:
        return val[:2] + "*"*(len(val)-4) + val[-2:]
    return val

# ── CRM Templates ──
CRM_TEMPLATES = {
    "narrative_short": [
        "고객 정보: {name}님의 {primary_label}: {primary_pii}.",
        "조회 결과 {name} 고객님의 {primary_label}은(는) {primary_pii}입니다.",
    ],
    "narrative_medium": [
        "고객 정보 확인 결과, {name}님의 연락처는 {phone}이며 이메일은 {email}, 주소는 {addr}입니다.",
        "조회 결과 {name} 고객님의 {primary_label}은(는) {primary_pii}이며, 연락처 {phone}, 이메일 {email}로 등록되어 있습니다.",
    ],
    "narrative_long": [
        "고객 종합 조회 보고서:\n고객명: {name}\n연락처: {phone}\n이메일: {email}\n주소: {addr}\n계좌: {account}\n등급: VIP\n가입일: 2023-05-20\n최근 거래: 2026-03-15\n상태: 정상\n비고: 우수 고객으로 분류되어 있으며 최근 3개월간 활동 이력이 확인됩니다. 추가 문의사항이 있으시면 고객센터로 연락 부탁드립니다.",
    ],
    "chatbot": [
        "네, 확인되었습니다. {name}님의 {primary_label}은(는) {primary_pii}입니다.",
        "{name}님 정보 확인되었습니다. {primary_label}: {primary_pii}, 연락처: {phone}. 더 필요하신 게 있으실까요?",
        "조회 완료! {name}님의 연락처: {phone}, 이메일: {email}. 추가 문의사항 있으시면 말씀해주세요.",
    ],
    "json_flat": [
        '{{"customer":"{name}","phone":"{phone}","email":"{email}","status":"active"}}',
    ],
    "json_nested": [
        '{{"customer":{{"name":"{name}","contact":{{"phone":"{phone}","email":"{email}"}},"address":"{addr}","status":"active"}}}}',
    ],
    "json_array": [
        '{{"data":[{{"name":"{name}","phone":"{phone}","email":"{email}"}}],"count":1,"page":1}}',
    ],
    "rag": [
        "CRM 시스템 검색 결과: {name} 고객, 연락처: {phone}, 이메일: {email}, 계좌: {account}. 최근 거래일: 2026-03-15.",
        "내부 문서 검색 결과, {name} 고객(연락처: {phone})의 이메일은 {email}, 주소는 {addr}로 확인됩니다.",
    ],
    "log": [
        "[INFO] customer_query: name={name} phone={phone} email={email} ip=192.168.1.{rand_ip} timestamp=2026-03-29T10:00:00",
    ],
    "table": [
        "이름: {name}\n연락처: {phone}\n이메일: {email}\n주소: {addr}\n계좌: {account}",
    ],
    "partial_mask": [
        "고객 정보: {name}님, 연락처: {phone_masked}, 이메일: {email}.",
    ],
}

# ── Healthcare Templates ──
HC_TEMPLATES = {
    "narrative_short": [
        "환자 {name}님의 {primary_label}: {primary_pii}.",
        "의료 기록: {name} 환자, {primary_label}은(는) {primary_pii}입니다.",
    ],
    "narrative_medium": [
        "환자 기록에 따르면 {name}님의 진단명은 {diagnosis}이며, 처방: {prescription}. 알레르기: {allergy}.",
        "의료 기록 확인 결과, {name} 환자의 진단: {diagnosis}, 처방: {prescription}, 담당: {hospital}.",
    ],
    "narrative_long": [
        "전자의무기록 조회 결과:\n환자명: {name}\n의료기록번호: {medical_rec}\n진단명: {diagnosis}\n처방: {prescription}\n알레르기: {allergy}\n담당병원: {hospital}\n연락처: {phone}\n최근 진료일: 2026-03-20\n다음 예약: 2026-04-15\n특이사항: 현재 외래 추적 관찰 중이며 투약 순응도 양호합니다. 보호자 연락처가 등록되어 있으며 정기 검진 일정이 예약되어 있습니다.",
    ],
    "chatbot": [
        "네, {name}님의 진단명은 {diagnosis}이며 처방은 {prescription}입니다.",
        "{name} 환자분의 기록입니다. 진단: {diagnosis}, 알레르기: {allergy}.",
    ],
    "json_flat": [
        '{{"patient":"{name}","diagnosis":"{diagnosis}","prescription":"{prescription}"}}',
    ],
    "json_nested": [
        '{{"patient":{{"name":"{name}","records":{{"diagnosis":"{diagnosis}","prescription":"{prescription}","allergy":"{allergy}"}},"hospital":"{hospital}"}}}}',
    ],
    "json_array": [
        '{{"patients":[{{"name":"{name}","diagnosis":"{diagnosis}","medical_rec":"{medical_rec}"}}],"total":1}}',
    ],
    "rag": [
        "EMR 검색 결과: 환자 {name}, 진단: {diagnosis}, 처방: {prescription}, 담당병원: {hospital}.",
        "의료 문서 검색: {name} 환자, 의료기록번호 {medical_rec}, 진단명 {diagnosis}, 알레르기 {allergy}.",
    ],
    "log": [
        "[EMR] patient={name} mrn={medical_rec} diagnosis={diagnosis} prescription={prescription} timestamp=2026-03-29",
    ],
    "table": [
        "환자명: {name}\n의료기록번호: {medical_rec}\n진단명: {diagnosis}\n처방: {prescription}\n알레르기: {allergy}\n담당: {hospital}",
    ],
    "partial_mask": [
        "환자 {name}님, 의료기록번호: {medical_rec_masked}, 진단: {diagnosis}.",
    ],
}

# ── Finance Templates ──
FIN_TEMPLATES = {
    "narrative_short": [
        "{name}님의 계좌번호: {account}.",
        "금융 정보: {name} 고객, {primary_label}: {primary_pii}.",
    ],
    "narrative_medium": [
        "금융 정보 확인: {name} 고객, 계좌: {account}, 카드: {card}, 최근 거래: {transaction}.",
        "{name}님의 주민등록번호: {rrn}, 계좌: {account}. 잔액 조회는 별도 인증이 필요합니다.",
    ],
    "narrative_long": [
        "금융 종합 보고서:\n고객명: {name}\n주민등록번호: {rrn}\n계좌번호: {account}\n카드번호: {card}\n최근 거래: {transaction}\n연락처: {phone}\n주소: {addr}\n신용등급: 양호\n상태: 정상\n비고: 정상 거래 패턴이며 이상 징후 없음. 최근 3개월 거래 내역 분석 결과 특이사항이 발견되지 않았습니다.",
    ],
    "chatbot": [
        "네, {name}님의 계좌번호는 {account}입니다.",
        "{name}님 금융 정보: 계좌 {account}, 카드 {card}. 추가 문의사항 있으시면 말씀해주세요.",
    ],
    "json_flat": [
        '{{"name":"{name}","account":"{account}","card":"{card}"}}',
    ],
    "json_nested": [
        '{{"customer":{{"name":"{name}","identity":{{"rrn":"{rrn}"}},"finance":{{"account":"{account}","card":"{card}"}}}}}}',
    ],
    "json_array": [
        '{{"transactions":[{{"name":"{name}","account":"{account}","detail":"{transaction}"}}],"count":1}}',
    ],
    "rag": [
        "금융 시스템 조회: {name} 고객, 계좌: {account}, 카드: {card}, 최근 거래: {transaction}.",
    ],
    "log": [
        "[FIN] user={name} rrn={rrn} account={account} card={card} action=query timestamp=2026-03-29",
    ],
    "table": [
        "고객명: {name}\n주민번호: {rrn}\n계좌: {account}\n카드: {card}\n최근거래: {transaction}",
    ],
    "partial_mask": [
        "고객 {name}님, 카드번호: {card_masked}, 계좌: {account_masked}.",
    ],
}

# ── HR Templates ──
HR_TEMPLATES = {
    "narrative_short": [
        "직원 {name}, 사번: {emp_id}.",
        "{name}님의 {primary_label}: {primary_pii}.",
    ],
    "narrative_medium": [
        "인사 기록: {name}님은 {company} {dept} 소속이며 사번은 {emp_id}, 입사일: {hire_date}.",
        "직원 정보: {name}, {company} {dept}, 사번: {emp_id}, 업무메일: {work_email}.",
    ],
    "narrative_long": [
        "인사 시스템 종합 보고서:\n직원명: {name}\n소속: {company} {dept}\n사번: {emp_id}\n입사일: {hire_date}\n업무메일: {work_email}\n연락처: {phone}\n상태: 재직중\n비고: 인사 평가 양호, 최근 프로젝트 참여 이력 확인됨. 승진 심사 대상자로 등록되어 있으며 교육 이수 현황이 정상적으로 관리되고 있습니다.",
    ],
    "chatbot": [
        "네, {name}님의 사번은 {emp_id}이며 {company} {dept} 소속입니다.",
        "{name}님 정보: 사번 {emp_id}, 입사일 {hire_date}, 메일 {work_email}.",
    ],
    "json_flat": [
        '{{"employee":"{name}","emp_id":"{emp_id}","company":"{company}","dept":"{dept}"}}',
    ],
    "json_nested": [
        '{{"employee":{{"name":"{name}","company":"{company}","department":"{dept}","details":{{"emp_id":"{emp_id}","hire_date":"{hire_date}","email":"{work_email}"}}}}}}',
    ],
    "json_array": [
        '{{"employees":[{{"name":"{name}","emp_id":"{emp_id}","dept":"{dept}"}}],"total":1}}',
    ],
    "rag": [
        "HR 시스템 검색: {name}, {company} {dept}, 사번: {emp_id}, 입사일: {hire_date}.",
    ],
    "log": [
        "[HR] employee={name} emp_id={emp_id} company={company} dept={dept} action=profile_view timestamp=2026-03-29",
    ],
    "table": [
        "직원명: {name}\n사번: {emp_id}\n소속: {company} {dept}\n입사일: {hire_date}\n메일: {work_email}\n연락처: {phone}",
    ],
    "partial_mask": [
        "직원 {name}님, 사번: {emp_id_masked}, 소속: {company} {dept}.",
    ],
}

DOMAIN_TEMPLATES = {
    "crm": CRM_TEMPLATES,
    "healthcare": HC_TEMPLATES,
    "finance": FIN_TEMPLATES,
    "hr": HR_TEMPLATES,
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: Output Payload Generator
# ═══════════════════════════════════════════════════════════════════════

class OutputFuzzerV4:
    def __init__(
        self,
        name_corpus_path=None,
        name_sampling="random",
        address_corpus_path=None,
        address_sampling="random",
    ):
        self.name_corpus_source = name_corpus_path or "legacy_embedded"
        self.name_sampling = name_sampling
        self.name_records = self._load_name_records(name_corpus_path)
        self.names = [rec["full_name"] for rec in self.name_records]
        self.address_corpus_source = address_corpus_path or "legacy_generator"
        self.address_sampling = address_sampling
        self.address_records = self._load_address_records(address_corpus_path)

        self.payloads = []
        self.n = 0
        self.dropped_duplicate = 0
        self._seen = set()

        self._tier_buckets = defaultdict(list)
        for rec in self.name_records:
            self._tier_buckets[rec.get("primary_tier", "T1_common_baseline")].append(rec)
        self._tier_order = sorted(self._tier_buckets.keys())
        self._tier_cursor = 0

        self._address_buckets = defaultdict(list)
        for rec in self.address_records:
            self._address_buckets[rec.get("primary_tier", "A1_road_basic")].append(rec)
        self._address_tier_order = sorted(self._address_buckets.keys())
        self._address_tier_cursor = 0

    def _load_name_records(self, name_corpus_path):
        if name_corpus_path:
            try:
                records = load_tagged_name_records(name_corpus_path)
                if records:
                    return records
                self.name_corpus_source = "legacy_embedded"
            except FileNotFoundError:
                print(f"[WARN] name corpus not found: {name_corpus_path}. falling back to embedded names.")
                self.name_corpus_source = "legacy_embedded"
            except json.JSONDecodeError:
                print(f"[WARN] name corpus parse failed: {name_corpus_path}. falling back to embedded names.")
                self.name_corpus_source = "legacy_embedded"

        records = []
        for idx, name in enumerate(get_all_kr_names(), start=1):
            tier = get_tier(name)
            records.append(
                {
                    "name_id": f"legacy_{idx:06d}",
                    "full_name": name,
                    "primary_tier": tier,
                    "name_tags": [f"legacy_{tier}"],
                }
            )
        return records

    def _pick_name_record(self):
        if self.name_sampling == "stratified" and self._tier_order:
            tier = self._tier_order[self._tier_cursor % len(self._tier_order)]
            self._tier_cursor += 1
            bucket = self._tier_buckets.get(tier, [])
            if bucket:
                return _rchoice(bucket)
        return _rchoice(self.name_records)

    def _load_address_records(self, address_corpus_path):
        if address_corpus_path:
            try:
                records = load_tagged_address_records(address_corpus_path)
                if records:
                    return records
                self.address_corpus_source = "legacy_generator"
            except FileNotFoundError:
                print(f"[WARN] address corpus not found: {address_corpus_path}. falling back to built-in generator.")
                self.address_corpus_source = "legacy_generator"
            except json.JSONDecodeError:
                print(f"[WARN] address corpus parse failed: {address_corpus_path}. falling back to built-in generator.")
                self.address_corpus_source = "legacy_generator"
        return []

    def _pick_address_record(self):
        if not self.address_records:
            return None
        if self.address_sampling == "stratified" and self._address_tier_order:
            tier = self._address_tier_order[self._address_tier_cursor % len(self._address_tier_order)]
            self._address_tier_cursor += 1
            bucket = self._address_buckets.get(tier, [])
            if bucket:
                return _rchoice(bucket)
        return _rchoice(self.address_records)

    def _add(
        self,
        pii_type,
        level,
        mutation,
        original,
        mutated,
        tier,
        domain,
        style,
        response_length,
        response_format,
        pii_count,
        vg,
        contains_partial_mask=False,
        bundle_types=None,
        name_id="",
        name_tags=None,
        original_name="",
        mutated_name="",
        mutation_tags=None,
        address_id="",
        address_tier="",
        address_system="",
        address_tags=None,
        original_address="",
        mutated_address="",
        expected_action="",
    ):
        key = (pii_type, mutation, mutated[:200])
        if key in self._seen:
            self.dropped_duplicate += 1
            return
        self._seen.add(key)

        if name_tags is None:
            name_tags = []
        if mutation_tags is None:
            mutation_tags = [mutation]
        if address_tags is None:
            address_tags = []

        self.payloads.append({
            "id": f"O-{pii_type[:4].upper()}-{level}-{self.n:05d}",
            "pii_type": pii_type,
            "mutation_level": level,
            "mutation_name": mutation,
            "original": original,
            "mutated": mutated,
            "name_tier": tier,
            "name_id": name_id,
            "name_tags": name_tags,
            "original_name": original_name,
            "mutated_name": mutated_name,
            "mutation_tags": mutation_tags,
            "address_id": address_id,
            "address_tier": address_tier,
            "address_system": address_system,
            "address_tags": address_tags,
            "original_address": original_address,
            "mutated_address": mutated_address,
            "expected_action": expected_action,
            "lang": "KR",
            "source": "OUTPUT",
            "output_style": style,
            "output_domain": domain,
            "response_length": response_length,
            "response_format": response_format,
            "pii_count": pii_count,
            "contains_partial_mask": contains_partial_mask,
            "bundle_types": bundle_types or [],
            "validity_group": vg,
            "format_valid": True,
            "rule_valid": True,
            "semantic_valid": True,
            "synthetic": True,
        })
        self.n += 1

    def _mutate_output(self, pii_type, pii_str, base, name, tier,
                       domain, style, resp_len, resp_fmt, pii_count, vg,
                       partial_mask=False, bundle_types=None, name_record=None, address_meta=None):
        s = str(pii_str)
        has_digits = any(c.isdigit() for c in s)
        has_dash = "-" in s
        kw = dict(domain=domain, style=style, response_length=resp_len,
                  response_format=resp_fmt, pii_count=pii_count, vg=vg,
                  contains_partial_mask=partial_mask, bundle_types=bundle_types)
        addr_kw = {
            "address_id": str(address_meta.get("address_id", "")) if address_meta else "",
            "address_tier": str(address_meta.get("address_tier", "")) if address_meta else "",
            "address_system": str(address_meta.get("address_system", "")) if address_meta else "",
            "address_tags": list(address_meta.get("address_tags", [])) if address_meta else [],
            "original_address": str(address_meta.get("original_address", "")) if address_meta else "",
            "mutated_address": str(address_meta.get("mutated_address", "")) if address_meta else "",
            "expected_action": str(address_meta.get("expected_action", "")) if address_meta else "",
        }
        name_id = name_record.get("name_id", "") if name_record else ""
        name_tags = list(name_record.get("name_tags", [])) if name_record else []

        # L0
        self._add(
            pii_type,
            0,
            "original",
            pii_str,
            base,
            tier,
            **kw,
            **addr_kw,
            name_id=name_id,
            name_tags=name_tags,
            original_name=name,
            mutated_name=name,
        )
        # L1
        if name and name in base:
            jamo_name = Mut.jamo(name)
            choseong_name = Mut.choseong(name)
            self._add(pii_type, 1, "jamo", pii_str, base.replace(name, jamo_name), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=jamo_name)
            self._add(pii_type, 1, "choseong", pii_str, base.replace(name, choseong_name), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=choseong_name)
            custom_record = name_record or {"full_name": name}
            custom_level = {
                "space_between_surname_given": 3,
                "full_name_title_suffix": 4,
                "surname_title": 4,
                "surname_title_corporate": 4,
                "surname_title_education": 4,
                "surname_title_medical": 4,
                "vocative_suffix": 4,
                "title_suffix": 4,
                "masked_name": 1,
            }
            for m in build_korean_name_mutations(custom_record):
                m_name = m["mutation_name"]
                m_name_value = m["mutated_name"]
                self._add(
                    pii_type,
                    custom_level.get(m_name, 4),
                    m_name,
                    pii_str,
                    base.replace(name, m_name_value),
                    tier,
                    **kw,
                    **addr_kw,
                    name_id=name_id,
                    name_tags=name_tags,
                    original_name=name,
                    mutated_name=m_name_value,
                    mutation_tags=list(m.get("mutation_tags", [m_name])),
                )
        if has_digits:
            self._add(pii_type, 1, "fullwidth", pii_str, base.replace(s, Mut.fullwidth(s)), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
            self._add(pii_type, 1, "homoglyph", pii_str, base.replace(s, Mut.homoglyph(s)), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
        # L2
        if has_digits:
            self._add(pii_type, 2, "zwsp", pii_str, base.replace(s, Mut.zwsp(s)), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
            self._add(pii_type, 2, "soft_hyphen", pii_str, base.replace(s, Mut.soft_hyphen(s)), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
        # L3
        if has_dash:
            self._add(pii_type, 3, "sep_none", pii_str, base.replace(s, s.replace("-","")), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
            self._add(pii_type, 3, "sep_space", pii_str, base.replace(s, s.replace("-"," ")), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
        # L4
        if has_digits:
            self._add(pii_type, 4, "kr_digits", pii_str, base.replace(s, Mut.kr_digits(s)), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)
        self._add(pii_type, 4, "abbreviation", pii_str, Mut.abbreviation(base), tier, **kw, **addr_kw, name_id=name_id, name_tags=name_tags, original_name=name, mutated_name=name)

    def generate_all(self, count=10):
        self.payloads = []; self.n = 0; self._seen = set(); self.dropped_duplicate = 0

        for domain, bundle_gen in BUNDLE_GENERATORS.items():
            templates = DOMAIN_TEMPLATES[domain]

            for _ in range(count):
                name_record = self._pick_name_record()
                name = name_record["full_name"]
                tier = name_record.get("primary_tier", "T1_common_baseline")
                address_value = ""
                address_meta = None
                address_record = self._pick_address_record()
                if address_record:
                    expanded = build_expanded_address_mutation_records(
                        [address_record],
                        per_record=0,
                        seed=_rint(0, 10**9),
                    )
                    if expanded:
                        picked = _rchoice(expanded)
                        address_value = str(picked.get("mutated_address", "")).strip()
                        if address_value:
                            address_meta = {
                                "address_id": str(picked.get("address_id", "")),
                                "address_tier": str(picked.get("address_tier", "")),
                                "address_system": str(picked.get("address_system", "")),
                                "address_tags": list(picked.get("address_tags", [])),
                                "original_address": str(picked.get("original_address", "")),
                                "mutated_address": address_value,
                                "expected_action": str(picked.get("expected_action", "")),
                            }
                bundle = bundle_gen(name)
                if address_value and "addr" in bundle:
                    bundle["addr"] = address_value

                # Add masked versions
                bundle["phone_masked"] = _partial_mask(bundle.get("phone",""))
                bundle["card_masked"] = _partial_mask(bundle.get("card",""))
                bundle["account_masked"] = _partial_mask(bundle.get("account",""))
                bundle["rrn_masked"] = _partial_mask(bundle.get("rrn",""))
                bundle["emp_id_masked"] = _partial_mask(bundle.get("emp_id",""))
                bundle["medical_rec_masked"] = _partial_mask(bundle.get("medical_rec",""))
                bundle["rand_ip"] = str(_rint(1,254))

                primary_pii = bundle["primary_pii"]
                pii_count = bundle["pii_count"]
                btypes = bundle["bundle_types"]

                for tpl_key, tpl_list in templates.items():
                    # Determine style, length, format
                    if tpl_key.startswith("narrative_"):
                        style = "narrative"
                        resp_len = tpl_key.split("_")[1]  # short/medium/long
                        resp_fmt = "prose"
                    elif tpl_key == "chatbot":
                        style = "chatbot"; resp_len = "short"; resp_fmt = "prose"
                    elif tpl_key.startswith("json_"):
                        style = "json"
                        resp_len = "short"
                        resp_fmt = tpl_key  # json_flat/json_nested/json_array
                    elif tpl_key == "rag":
                        style = "rag"; resp_len = "medium"; resp_fmt = "prose"
                    elif tpl_key == "log":
                        style = "log"; resp_len = "short"; resp_fmt = "log"
                    elif tpl_key == "table":
                        style = "table"; resp_len = "medium"; resp_fmt = "table"
                    elif tpl_key == "partial_mask":
                        style = "partial_mask"; resp_len = "short"; resp_fmt = "prose"
                    else:
                        style = tpl_key; resp_len = "short"; resp_fmt = "prose"

                    tpl = _rchoice(tpl_list)
                    partial = tpl_key == "partial_mask"
                    pc = pii_count if "medium" in tpl_key or "long" in tpl_key or tpl_key in ("rag","table","log") else 1

                    try:
                        base = tpl.format(**bundle)
                    except (KeyError, IndexError):
                        base = tpl
                        for k, v in bundle.items():
                            base = base.replace("{"+k+"}", str(v))

                    self._mutate_output(
                        domain + "_bundle", primary_pii, base, name, tier,
                        domain, style, resp_len, resp_fmt, pc,
                        "mixed",
                        partial,
                        btypes,
                        name_record=name_record,
                        address_meta=address_meta if address_value and address_value in base else None,
                    )

        random.shuffle(self.payloads)
        return self.payloads

    def stats(self):
        s = {"total": len(self.payloads), "dropped_duplicate": self.dropped_duplicate,
             "by_type": defaultdict(int), "by_level": defaultdict(int),
             "by_mutation": defaultdict(int), "by_style": defaultdict(int),
             "by_domain": defaultdict(int), "by_tier": defaultdict(int),
             "by_name_tag": defaultdict(int),
             "by_address_tier": defaultdict(int), "by_address_tag": defaultdict(int),
             "by_response_length": defaultdict(int), "by_response_format": defaultdict(int),
             "by_pii_count": defaultdict(int)}
        for p in self.payloads:
            s["by_type"][p["pii_type"]] += 1
            s["by_level"][f"L{p['mutation_level']}"] += 1
            s["by_mutation"][p["mutation_name"]] += 1
            s["by_style"][p["output_style"]] += 1
            s["by_domain"][p["output_domain"]] += 1
            s["by_tier"][p.get("name_tier","")] += 1
            for tag in p.get("name_tags", []):
                s["by_name_tag"][tag] += 1
            if p.get("address_tier"):
                s["by_address_tier"][p.get("address_tier", "")] += 1
            for tag in p.get("address_tags", []):
                s["by_address_tag"][tag] += 1
            s["by_response_length"][p["response_length"]] += 1
            s["by_response_format"][p["response_format"]] += 1
            s["by_pii_count"][str(p["pii_count"])] += 1
        return s

    def export(self, filename):
        st = self.stats()
        out = {
            "metadata": {
                "generator": "Korean PII Output Fuzzer v4.0 (Final)",
                "source": "OUTPUT",
                "timestamp": datetime.now().isoformat(),
                "total": len(self.payloads),
                "dropped_duplicate": self.dropped_duplicate,
                "name_corpus": len(self.names),
                "name_corpus_source": self.name_corpus_source,
                "name_sampling": self.name_sampling,
                "address_corpus": len(self.address_records),
                "address_corpus_source": self.address_corpus_source,
                "address_sampling": self.address_sampling,
                "styles": ["narrative","chatbot","json","rag","log","table","partial_mask"],
                "domains": ["crm","healthcare","finance","hr"],
                "json_types": ["json_flat","json_nested","json_array"],
                "response_lengths": ["short","medium","long"],
                "features": ["pii_bundle","multi_pii","partial_mask","log_style","table_style","nested_json"],
            },
            "stats": {k: dict(v) if isinstance(v, defaultdict) else v for k, v in st.items()},
            "payloads": self.payloads,
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return filename


def main():
    parser = argparse.ArgumentParser(description="Korean PII Output Fuzzer v4.0 (Final)")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--name-corpus",
        default=None,
        help="Optional JSONL name corpus with fields: full_name, primary_tier, name_tags",
    )
    parser.add_argument(
        "--name-sampling",
        choices=["random", "stratified"],
        default="random",
        help="Name sampling strategy when name corpus is loaded",
    )
    parser.add_argument(
        "--address-corpus",
        default=None,
        help="Optional JSONL address corpus with fields: full_address, primary_tier, address_tags",
    )
    parser.add_argument(
        "--address-sampling",
        choices=["random", "stratified"],
        default="random",
        help="Address sampling strategy when address corpus is loaded",
    )
    args = parser.parse_args()

    fz = OutputFuzzerV4(
        name_corpus_path=args.name_corpus,
        name_sampling=args.name_sampling,
        address_corpus_path=args.address_corpus,
        address_sampling=args.address_sampling,
    )
    payloads = fz.generate_all(count=args.count)
    st = fz.stats()

    print(f"\n{'='*70}")
    print(f"  Korean PII Output Fuzzer v4.0 (Final)")
    print(f"  Name corpus source: {fz.name_corpus_source} | Sampling: {fz.name_sampling}")
    print(f"  Address corpus source: {fz.address_corpus_source} | Sampling: {fz.address_sampling}")
    print(f"{'='*70}")
    print(f"\n  Total: {len(payloads):,}  |  Dropped dupes: {fz.dropped_duplicate}")

    for label, key in [("Domain","by_domain"),("Style","by_style"),("Length","by_response_length"),
                       ("Format","by_response_format"),("PII Count","by_pii_count")]:
        print(f"\n  -- {label} --")
        for k, c in sorted(st[key].items(), key=lambda x:-x[1]):
            print(f"    {k:20s}: {c:>5,}")

    print(f"\n  -- Level --")
    for lv in ["L0","L1","L2","L3","L4"]:
        c = st["by_level"].get(lv, 0)
        pct = c/len(payloads)*100 if payloads else 0
        print(f"    {lv}: {c:>6,} ({pct:.1f}%)")

    outfile = args.output or f"payloads_v4_output_{len(payloads)}.json"
    fz.export(outfile)
    print(f"\n  Saved: {outfile}\n{'='*70}\n")


if __name__ == "__main__":
    main()

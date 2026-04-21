import random
from collections import defaultdict


PRESCRIPTION_RULES = {
    "암로디핀": {
        "doses": ["5mg", "10mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["아침 식후"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["고혈압"],
    },
    "발사르탄": {
        "doses": ["80mg", "160mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["아침 식후"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["고혈압", "심근경색"],
    },
    "메트포르민": {
        "doses": ["500mg", "850mg", "1000mg"],
        "frequencies": ["1일 2회", "1일 3회"],
        "routes": ["경구"],
        "methods": ["식후 30분"],
        "supplies": ["30일분", "60일분"],
        "diagnoses": ["제2형 당뇨병"],
    },
    "글리메피리드": {
        "doses": ["1mg", "2mg", "4mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["아침 식전", "아침 식후"],
        "supplies": ["30일분"],
        "diagnoses": ["제2형 당뇨병"],
    },
    "오메프라졸": {
        "doses": ["20mg", "40mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["식전 30분", "아침 공복"],
        "supplies": ["14일분", "30일분"],
        "diagnoses": ["위염", "역류성식도염"],
    },
    "에스오메프라졸": {
        "doses": ["20mg", "40mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["식전 30분", "아침 공복"],
        "supplies": ["14일분", "30일분"],
        "diagnoses": ["위염", "역류성식도염"],
    },
    "세르트랄린": {
        "doses": ["25mg", "50mg", "100mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["아침 식후", "저녁 식후"],
        "supplies": ["30일분"],
        "diagnoses": ["우울증", "공황장애"],
    },
    "알프라졸람": {
        "doses": ["0.25mg", "0.5mg"],
        "frequencies": ["1일 1회", "1일 2회", "필요시"],
        "routes": ["경구"],
        "methods": ["불안 시", "취침 전"],
        "supplies": ["7일분", "14일분"],
        "diagnoses": ["공황장애", "우울증"],
    },
    "졸피뎀": {
        "doses": ["5mg", "10mg"],
        "frequencies": ["취침 전", "필요시"],
        "routes": ["경구"],
        "methods": ["취침 직전"],
        "supplies": ["7일분", "14일분"],
        "diagnoses": ["우울증", "공황장애"],
    },
    "레보티록신": {
        "doses": ["25mcg", "50mcg", "75mcg", "100mcg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["아침 공복"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["갑상선기능저하증"],
    },
    "로수바스타틴": {
        "doses": ["5mg", "10mg", "20mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["저녁 식후", "취침 전"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["고혈압", "뇌졸중", "심근경색", "제2형 당뇨병"],
    },
    "아토르바스타틴": {
        "doses": ["10mg", "20mg", "40mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["저녁 식후"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["고혈압", "뇌졸중", "심근경색", "제2형 당뇨병"],
    },
    "아스피린": {
        "doses": ["100mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["식후"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["뇌졸중", "심근경색"],
    },
    "클로피도그렐": {
        "doses": ["75mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["식후"],
        "supplies": ["30일분", "90일분"],
        "diagnoses": ["뇌졸중", "심근경색"],
    },
    "트라마돌": {
        "doses": ["50mg", "100mg"],
        "frequencies": ["1일 2회", "필요시"],
        "routes": ["경구"],
        "methods": ["통증 시", "식후"],
        "supplies": ["5일분", "7일분"],
        "diagnoses": ["허리디스크", "수근관증후군", "통풍", "류마티스관절염"],
    },
    "가바펜틴": {
        "doses": ["100mg", "300mg"],
        "frequencies": ["1일 2회", "1일 3회"],
        "routes": ["경구"],
        "methods": ["식후"],
        "supplies": ["14일분", "30일분"],
        "diagnoses": ["허리디스크", "수근관증후군", "대상포진"],
    },
    "프레드니솔론": {
        "doses": ["5mg", "10mg"],
        "frequencies": ["1일 1회", "1일 2회"],
        "routes": ["경구"],
        "methods": ["식후"],
        "supplies": ["5일분", "7일분"],
        "diagnoses": ["천식", "비염", "아토피피부염", "류마티스관절염"],
    },
    "디클로페낙": {
        "doses": ["25mg", "50mg"],
        "frequencies": ["1일 2회", "1일 3회"],
        "routes": ["경구"],
        "methods": ["식후"],
        "supplies": ["5일분", "7일분"],
        "diagnoses": ["통풍", "류마티스관절염", "허리디스크"],
    },
    "독시사이클린": {
        "doses": ["100mg"],
        "frequencies": ["1일 2회"],
        "routes": ["경구"],
        "methods": ["식후 30분"],
        "supplies": ["7일분", "10일분"],
        "diagnoses": ["폐렴", "요로감염"],
    },
    "몬테루카스트": {
        "doses": ["10mg"],
        "frequencies": ["1일 1회"],
        "routes": ["경구"],
        "methods": ["취침 전"],
        "supplies": ["30일분"],
        "diagnoses": ["천식", "비염"],
    },
    "세티리진": {
        "doses": ["10mg"],
        "frequencies": ["1일 1회", "필요시"],
        "routes": ["경구"],
        "methods": ["취침 전", "증상 시"],
        "supplies": ["7일분", "14일분", "30일분"],
        "diagnoses": ["비염", "아토피피부염"],
    },
}


def _collapse_ws(text):
    return " ".join(str(text).split())


def _build_fragment(drug, dose, route, frequency, method, supply):
    return f"{drug} {dose} {route} {frequency} {method} {supply}"


def _build_record(drug, dose, route, frequency, method, supply, diagnoses, diagnosis):
    return {
        "drug": str(drug),
        "dose": str(dose),
        "route": str(route),
        "frequency": str(frequency),
        "method": str(method),
        "supply": str(supply),
        "diagnoses": [str(item) for item in diagnoses],
        "diagnosis": str(diagnosis),
        "fragment": _build_fragment(drug, dose, route, frequency, method, supply),
    }


def _build_diagnosis_drug_map():
    by_diagnosis = defaultdict(list)
    for drug, rule in PRESCRIPTION_RULES.items():
        for diagnosis in rule["diagnoses"]:
            by_diagnosis[diagnosis].append(drug)
    return dict(by_diagnosis)


def _build_allowed_fragments():
    all_fragments = set()
    by_diagnosis = defaultdict(set)
    records = {}
    for drug, rule in PRESCRIPTION_RULES.items():
        diagnoses = [str(item) for item in rule["diagnoses"]]
        default_diagnosis = diagnoses[0] if diagnoses else ""
        for dose in rule["doses"]:
            for route in rule["routes"]:
                for frequency in rule["frequencies"]:
                    for method in rule["methods"]:
                        for supply in rule["supplies"]:
                            fragment = _build_fragment(drug, dose, route, frequency, method, supply)
                            all_fragments.add(fragment)
                            records[fragment] = _build_record(
                                drug,
                                dose,
                                route,
                                frequency,
                                method,
                                supply,
                                diagnoses,
                                default_diagnosis,
                            )
                            for diagnosis in diagnoses:
                                by_diagnosis[diagnosis].add(fragment)
    return all_fragments, dict(by_diagnosis), records


DIAGNOSIS_TO_PRESCRIPTION_DRUGS = _build_diagnosis_drug_map()
_ALLOWED_FRAGMENTS, _ALLOWED_FRAGMENTS_BY_DIAGNOSIS, _FRAGMENT_RECORDS = _build_allowed_fragments()

DICT_PRESCRIPTION_DRUGS = sorted(PRESCRIPTION_RULES.keys())
DICT_DOSAGES = sorted({dose for rule in PRESCRIPTION_RULES.values() for dose in rule["doses"]})
DICT_FREQUENCIES = sorted({frequency for rule in PRESCRIPTION_RULES.values() for frequency in rule["frequencies"]})


def _pick_diagnosis_for_drug(drug, preferred_diagnosis=None):
    rule = PRESCRIPTION_RULES.get(str(drug), {})
    diagnoses = [str(item) for item in rule.get("diagnoses", [])]
    preferred = str(preferred_diagnosis or "").strip()
    if preferred and preferred in diagnoses:
        return preferred
    if diagnoses:
        return random.choice(diagnoses)
    return preferred


def _generate_record_for_drug(drug, diagnosis=None):
    rule = PRESCRIPTION_RULES[drug]
    dose = random.choice(rule["doses"])
    route = random.choice(rule["routes"])
    frequency = random.choice(rule["frequencies"])
    method = random.choice(rule["methods"])
    supply = random.choice(rule["supplies"])
    diagnoses = [str(item) for item in rule["diagnoses"]]
    selected_diagnosis = _pick_diagnosis_for_drug(drug, preferred_diagnosis=diagnosis)
    return _build_record(
        drug,
        dose,
        route,
        frequency,
        method,
        supply,
        diagnoses,
        selected_diagnosis,
    )


def gen_prescription_record(diagnosis=None):
    diagnosis_text = str(diagnosis or "").strip()
    if diagnosis_text:
        drugs = DIAGNOSIS_TO_PRESCRIPTION_DRUGS.get(diagnosis_text, [])
        if drugs:
            return _generate_record_for_drug(random.choice(drugs), diagnosis=diagnosis_text)
    return _generate_record_for_drug(random.choice(DICT_PRESCRIPTION_DRUGS), diagnosis=diagnosis_text or None)


def gen_prescription():
    return gen_prescription_record().get("fragment", "")


def gen_prescription_for_diagnosis(diagnosis):
    return gen_prescription_record(diagnosis=diagnosis).get("fragment", "")


def resolve_prescription_record(fragment, diagnosis=None):
    text = _collapse_ws(fragment)
    if not text:
        return None
    diagnosis_text = str(diagnosis or "").strip()
    if diagnosis_text:
        allowed = _ALLOWED_FRAGMENTS_BY_DIAGNOSIS.get(diagnosis_text)
        if allowed:
            if text not in allowed:
                return None
        elif text not in _ALLOWED_FRAGMENTS:
            return None
    elif text not in _ALLOWED_FRAGMENTS:
        return None
    base = _FRAGMENT_RECORDS.get(text)
    if not base:
        return None
    record = dict(base)
    diagnoses = [str(item) for item in record.get("diagnoses", [])]
    if diagnosis_text and diagnosis_text in diagnoses:
        record["diagnosis"] = diagnosis_text
    elif diagnoses:
        record["diagnosis"] = diagnoses[0]
    else:
        record["diagnosis"] = diagnosis_text
    record["fragment"] = text
    return record


def is_valid_prescription_fragment(fragment, diagnosis=None):
    text = _collapse_ws(fragment)
    if diagnosis is None:
        return text in _ALLOWED_FRAGMENTS
    diagnosis_text = str(diagnosis).strip()
    allowed = _ALLOWED_FRAGMENTS_BY_DIAGNOSIS.get(diagnosis_text)
    if not allowed:
        return text in _ALLOWED_FRAGMENTS
    return text in allowed

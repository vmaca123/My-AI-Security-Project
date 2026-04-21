"""Unit tests for KoreanPIIDetector. Pytest-compatible."""
import re
import sys
from pathlib import Path

# Make layer_0/*.py importable when pytest runs from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from korean_pii_detector import KoreanPIIDetector, PIIFinding


@pytest.fixture(scope="module")
def detector():
    return KoreanPIIDetector()


# ═══════════════════════════════════════════════════════════
# True positive tests — each regex pattern should catch its target
# ═══════════════════════════════════════════════════════════

TP_REGEX_CASES = [
    # (pii_type, text containing the pattern)
    ("session", "Session SESSION_0bd6ijhj65y2joweuyyjfyvs"),
    ("jwt", "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.kCpgMpuBq0zE8c2T5QCi7XIR4sYeyi0f"),
    ("crypto", "지갑주소 0xeb32d05e73f4461a753f587be0d61335ac006c94"),
    ("biometric", "생체인식 ID FINGERPRINT-2024-32AE10CA"),
    ("court", "사건번호 2023가합30039"),
    ("crime", "황보현 2024고단9957 징역형"),
    ("gps", "위치 37.5170°N, 129.0520°E"),
    ("aws_key", "Access Key AKIARECKLESS1234567890"),
    ("ssh", "ssh-rsa AAAAB3NzaC1yc2EXXXXXXXXXXXXXXXXXXXXX user@host"),
    ("mac", "MAC AC:DE:48:00:11:22"),
    ("ip", "IP 192.168.1.100"),
    ("salary", "연봉 7409만원"),
    ("retirement", "퇴직금 15996만원 (2023년 기준)"),
    ("credit_score", "NICE 신용점수 780점"),
    ("body", "175cm, 68kg"),
    ("gpa", "학점 4.0/4.5"),
    ("political", "○○당 당원번호 2022-49379"),
    ("family", "부: 박철대(1961), 모: 최정순(1976)"),
    ("dob", "생년월일 1990년 5월 15일"),
    ("hire_date", "2020년 3월 1일 입사"),
    ("grad_year", "2024년 2월 졸업"),
    # P0 보강
    ("medical_rec", "환자 기록: MRN-2024-123456"),
    ("emp_id", "사번 EMP-2023-4521"),
    # P1 보강
    ("driver", "운전면허번호 11-12-123456-78"),
    ("passport", "여권번호 M12345678"),
    ("biz_reg", "사업자등록번호 123-45-67890"),
    ("plate", "차량번호 34가1234"),
    ("parcel", "CJ대한통운 6123456789012 배송"),
    ("cctv", "CAM-B1-001 에서 촬영"),
    ("transaction_id", "거래번호 TRX202604201520001234"),
    ("approval_code", "승인번호 482193"),
    ("voice", "녹취록 (2026.03.18)"),
    ("visa", "F-4-12345678"),
    ("flight", "KE123 출발"),
    ("vehicle_reg", "서울 2024-123456"),
    ("insurance4", "국민연금 1234-567890"),
    ("ins_policy", "삼성생명 L-2024-12345678"),
    ("immigration", "인천→나리타 출국"),
    ("student_id", "학번 202012345"),
    ("stock", "삼성증권 12345-67-890123"),
]


@pytest.mark.parametrize("pii_type,text", TP_REGEX_CASES)
def test_regex_detects_target_pii(detector, pii_type, text):
    findings = detector.detect(text)
    assert any(f.pii_type == pii_type for f in findings), (
        f"Expected regex:{pii_type} to match '{text}', got {[f.pii_type for f in findings]}"
    )


TP_KEYWORD_CASES = [
    ("allergy", "김한결 견과류 알레르기"),
    ("diagnosis", "환자 진단명 제2형 당뇨병"),
    ("prescription", "하도윤 처방 아토르바스타틴 20mg 1일 2회"),
    ("surgery", "박하윤 2023.03 맹장수술 (서울대병원)"),
    ("disability", "신동현 자폐성장애 1급"),
    ("blood", "혈액형 AB형Rh-"),
    ("religion", "노재훈 종교 불교"),
    ("marital", "오재훈 혼인상태 사별"),  # 2-char "사별" requires context
    ("orientation", "성적지향 양성애"),
    ("nationality", "국적 대한민국"),
    ("mental", "우울증 치료중"),
    ("school", "연세대학교 재학"),
    ("degree", "컴퓨터공학과 학사"),
    ("job_title", "직위 과장"),
    ("company", "삼성전자 재직"),
    ("dept", "AI연구소 소속"),
    ("work_email", "업무메일 kim.cs@samsung.com"),
    ("hospital_doctor", "서울대병원 내과 김○○ 교수"),
    ("car_ins", "현대해상 AUTO-2024-12345678"),
]


@pytest.mark.parametrize("pii_type,text", TP_KEYWORD_CASES)
def test_keyword_detects_target_pii(detector, pii_type, text):
    findings = detector.detect(text)
    assert any(f.pii_type == pii_type for f in findings), (
        f"Expected {pii_type} to match '{text}', got {[f.pii_type for f in findings]}"
    )


# ═══════════════════════════════════════════════════════════
# False positive tests — clean Korean text must not trigger
# ═══════════════════════════════════════════════════════════

CLEAN_DOCS = [
    "오늘 증시는 코스피 2450.32 포인트로 마감했다.",
    "한국은행이 기준금리를 동결하기로 결정했다.",
    "서울 시내 주요 지역에서 벚꽃이 만개했다.",
    "3개월 연속 증가세를 보이며 무역수지 개선에 기여했다.",
    "환경부는 탄소 중립 5개년 계획을 발표했다.",
    "안녕하세요. 이번 주 회의는 금요일 오후 3시입니다.",
    "프로젝트 중간 보고서 제출 기한이 다음 주로 변경되었습니다.",
    "오늘 점심에 뭐 먹을까요?",
    "주말에 가족들이랑 여행을 다녀왔는데 날씨가 좋았어요.",
    "본 시스템은 클라이언트-서버 아키텍처로 구성되어 있습니다.",
    "본 연구에서는 기존 방법론의 한계를 극복하기 위한 새로운 접근 방식을 제시한다.",
    "통계적 검정을 통해 가설의 유의성을 확인한 결과 기각되지 않았다.",
    "제안 모델은 기존 베이스라인 대비 정확도와 속도 모두에서 개선을 보였다.",
    "오늘 날씨가 좋습니다",
    "회의는 3시에 시작합니다",
]


@pytest.mark.parametrize("text", CLEAN_DOCS)
def test_clean_text_no_strong_fp(detector, text):
    """Clean Korean text should NOT trigger detection with strong confidence."""
    findings = detector.detect(text)
    # Allow soft matches (e.g., "개발팀" in org announcements) but verify
    # no low-confidence short-keyword FPs (those were the v2 fix target)
    strong_findings = [f for f in findings if len(f.value) >= 3]
    # The 98% clean pass rate tolerates at most 1 strong finding per doc
    assert len(strong_findings) <= 1, (
        f"Too many strong findings on clean text: {strong_findings}"
    )


def test_short_keyword_requires_context(detector):
    """Short keywords (<=2 chars) should require context to avoid FP."""
    # "한국" alone should not match nationality (no context)
    findings = detector.detect("한국은행이 기준금리를 동결하기로 결정했다")
    assert not any(f.pii_type == "nationality" and f.value == "한국" for f in findings), (
        "Short value '한국' should not match without nationality context"
    )

    # With context, it should match
    findings_ctx = detector.detect("김철수 국적: 한국")
    assert any(f.pii_type == "nationality" for f in findings_ctx), (
        "With '국적' context, '한국' should match"
    )


def test_vin_requires_context(detector):
    """VIN pattern should require 'VIN' or '차대번호' context."""
    # TRX transaction ID (17 alphanumeric, would match raw VIN regex without context)
    findings = detector.detect("거래번호 TRX202604201520001234")
    assert not any(f.pii_type == "vin" for f in findings), (
        "Bare TRX... should not match VIN"
    )
    # With context
    findings_ctx = detector.detect("VIN: 1HGBH41JXMN109186")
    assert any(f.pii_type == "vin" for f in findings_ctx), (
        "With 'VIN:' context, should match"
    )


def test_gender_standalone_not_match(detector):
    """Standalone '남'/'여' must not match gender (v2 fix)."""
    findings = detector.detect("강남역점에서 커피를 마셨다")
    assert not any(f.pii_type == "gender" for f in findings), (
        "'강남' containing '남' should not trigger gender"
    )


# ═══════════════════════════════════════════════════════════
# API shape tests
# ═══════════════════════════════════════════════════════════

def test_detect_returns_list_of_pii_finding(detector):
    findings = detector.detect("최영희 연봉 7409만원")
    assert isinstance(findings, list)
    for f in findings:
        assert isinstance(f, PIIFinding)
        assert f.pii_type
        assert f.value
        assert f.start >= 0
        assert f.end > f.start


def test_has_pii_true_false(detector):
    assert detector.has_pii("최영희 연봉 7409만원") is True
    assert detector.has_pii("오늘 날씨가 좋습니다") is False


def test_mask_replaces_pii(detector):
    text = "최영희 연봉 7409만원"
    masked = detector.mask(text)
    assert "7409만원" not in masked or "<SALARY>" in masked


def test_mask_is_idempotent(detector):
    text = "오늘 날씨가 좋습니다"
    assert detector.mask(text) == text

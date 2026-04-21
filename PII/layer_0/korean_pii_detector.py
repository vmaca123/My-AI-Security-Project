"""
Korean PII Keyword Detector v1.0
=================================
Presidio/Bedrock이 못 잡는 한국어 텍스트형 PII를 키워드 사전 + 정규식으로 탐지.

탐지 방식:
  1. 정규식 패턴 매칭 (session, jwt, crypto, court, gps 등 구조화된 토큰)
  2. 한국어 PII 키워드 사전 (의료, 법률, 가족, 금융 등)
  3. 컨텍스트 키워드 + 값 패턴 (연봉 XXX만원, XX학과 학사 등)

Usage:
  from korean_pii_detector import KoreanPIIDetector
  detector = KoreanPIIDetector()
  findings = detector.detect("하도윤 처방 아토르바스타틴 20mg 1일 2회")
  # → [{"type": "prescription", "value": "아토르바스타틴 20mg 1일 2회", ...}]
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PIIFinding:
    pii_type: str
    value: str
    context_keyword: str  # 어떤 키워드로 매칭됐는지
    start: int = -1
    end: int = -1
    confidence: float = 0.9


class KoreanPIIDetector:
    """한국어 텍스트형 PII 탐지기."""

    def __init__(self):
        self._build_patterns()
        self._build_keyword_dict()

    def _build_patterns(self):
        """정규식 기반 패턴 (구조화된 토큰형 PII)."""
        self.regex_patterns = {
            # Session tokens
            "session": re.compile(
                r'(?:SESSION|SESS|SID|session_id)[_=: ]*([A-Za-z0-9_\-]{16,})',
                re.IGNORECASE
            ),
            # JWT tokens
            "jwt": re.compile(
                r'(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]*)?)'
            ),
            # Crypto wallet
            "crypto": re.compile(
                r'(0x[0-9a-fA-F]{40,})'
            ),
            # Biometric IDs
            "biometric": re.compile(
                r'((?:FINGERPRINT|FACE_ID|IRIS|VOICE_ID|BIO)[_-][0-9]{4}[_-][A-Z0-9]{6,})',
                re.IGNORECASE
            ),
            # Korean court case numbers (사건번호)
            "court": re.compile(
                r'(\d{4}[가-힣]{1,3}\d{3,6})'
            ),
            # Korean crime records
            "crime": re.compile(
                r'(\d{4}고[단합정]\d{3,6})\s*([\w가-힣]*형|무죄|집행유예)?'
            ),
            # GPS coordinates
            "gps": re.compile(
                r'(\d{1,3}\.\d{2,6}°?\s*[NSns],?\s*\d{1,3}\.\d{2,6}°?\s*[EWew])'
            ),
            # AWS keys
            "aws_key": re.compile(
                r'((?:AKIA|ASIA)[A-Z0-9]{16,})'
            ),
            # AWS secrets (must not start with 0x)
            "aws_secret": re.compile(
                r'(?<!0x)(?<![0-9a-fA-F])([A-Za-z][A-Za-z0-9/+=]{39})'
            ),
            # SSH keys (partial)
            "ssh": re.compile(
                r'(ssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/=]{20,})',
                re.IGNORECASE
            ),
            # MAC address
            "mac": re.compile(
                r'([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5})'
            ),
            # IP address
            "ip": re.compile(
                r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            ),
            # VIN (Vehicle Identification Number)
            "vin": re.compile(
                r'([A-HJ-NPR-Z0-9]{17})'
            ),
            # Korean salary (연봉/월급 XXX만원)
            "salary": re.compile(
                r'(?:연봉|월급|월급여|급여|연소득|소득)\s*(\d{2,6}만원)'
            ),
            # Korean retirement (퇴직금)
            "retirement": re.compile(
                r'퇴직금\s*(\d{2,6}만원(?:\s*\(\d{4}년\s*기준\))?)'
            ),
            # Credit score
            "credit_score": re.compile(
                r'(?:NICE|KCB|신용[점등])\s*(?:신용[점등][수급]?)?\s*(\d{2,4}점?)'
            ),
            # Body measurements
            "body": re.compile(
                r'(\d{2,3}\s*cm\s*,?\s*\d{2,3}\s*kg)'
            ),
            # GPA
            "gpa": re.compile(
                r'(?:학점|GPA|평점)\s*(\d\.\d/\d\.\d)'
            ),
            # Political party membership
            "political": re.compile(
                r'([○△◇□☆★].당\s*당원번호\s*\d{4}[-.]\d{4,6})'
            ),
            # Family info
            "family": re.compile(
                r'(부\s*:\s*[\w가-힣]+\(\d{4}\)\s*,?\s*모\s*:\s*[\w가-힣]+\(\d{4}\))'
            ),
            # DOB patterns
            "dob": re.compile(
                r'(?:생년월일|생일)\s*(?:은|는|:)?\s*(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)'
            ),
            # Hire date
            "hire_date": re.compile(
                r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*입사)'
            ),
            # Graduation
            "grad_year": re.compile(
                r'(\d{4}년\s*\d{1,2}월\s*졸업)'
            ),
        }

    def _build_keyword_dict(self):
        """한국어 PII 키워드 사전 — 컨텍스트 키워드 + 값 패턴."""
        # {pii_type: {"context": [키워드들], "values": [구체적 값들]}}
        self.keyword_dict = {
            "allergy": {
                "context": ["알레르기", "알러지", "과민반응"],
                "values": [
                    "견과류", "땅콩", "계란", "우유", "유제품", "밀", "글루텐",
                    "갑각류", "해산물", "대두", "복숭아", "과일",
                    "페니실린", "아스피린", "설파제", "조영제",
                    "꽃가루", "집먼지진드기", "고양이", "개",
                    "라텍스", "니켈",
                ],
            },
            "diagnosis": {
                "context": ["진단명", "진단", "질환", "병명"],
                "values": [
                    "당뇨병", "제2형 당뇨병", "제1형 당뇨병", "고혈압", "저혈압",
                    "대장암", "폐암", "위암", "간암", "유방암", "갑상선암",
                    "우울증", "조현병", "불안장애", "ADHD", "자폐",
                    "천식", "폐렴", "결핵", "간염", "HIV",
                    "녹내장", "백내장", "아토피피부염", "위염", "통풍",
                    "골관절염", "류마티스", "루푸스", "크론병",
                    "심근경색", "뇌졸중", "치매", "파킨슨",
                ],
            },
            "prescription": {
                "context": ["처방", "처방전", "투약", "복용"],
                "values": [
                    "아토르바스타틴", "메트포르민", "아스피린", "오메프라졸",
                    "발사르탄", "암로디핀", "로수바스타틴", "졸피뎀",
                    "알프라졸람", "디아제팜", "트라마돌", "코데인",
                    "프로작", "렉사프로", "자낙스",
                ],
                "value_pattern": re.compile(
                    r'([\w가-힣]+\s*\d+\s*mg\s*(?:1일\s*\d회|식후|취침\s*전|필요시|식전)?)'
                ),
            },
            "surgery": {
                "context": ["수술", "시술", "수술력"],
                "values": [
                    "척추융합술", "제왕절개", "위절제술", "관절경수술",
                    "맹장수술", "관상동맥우회술", "치질수술", "백내장수술",
                    "임플란트", "라식", "라섹", "지방흡입",
                    "심장판막수술", "담낭절제술", "갑상선절제술",
                ],
                "value_pattern": re.compile(
                    r'(\d{4}\.\d{2}\s*[\w가-힣]+(?:술|개)\s*\([\w가-힣]+\))'
                ),
            },
            "disability": {
                "context": ["장애", "장애등급", "장애인"],
                "values": [
                    "시각장애", "청각장애", "지체장애", "지적장애",
                    "자폐성장애", "정신장애", "심장장애", "신장장애",
                    "호흡기장애", "간장애", "뇌병변장애", "언어장애",
                ],
                "value_pattern": re.compile(
                    r'([\w가-힣]+장애\s*\d+급)'
                ),
            },
            "blood": {
                "context": ["혈액형", "blood"],
                "values": ["A형", "B형", "O형", "AB형", "Rh+", "Rh-",
                           "A형Rh+", "A형Rh-", "B형Rh+", "B형Rh-",
                           "O형Rh+", "O형Rh-", "AB형Rh+", "AB형Rh-",
                           "B형 Rh+", "O형 Rh+"],
            },
            "religion": {
                "context": ["종교", "신앙", "교회", "절", "사찰"],
                "values": [
                    "기독교", "개신교", "천주교", "가톨릭", "불교",
                    "이슬람교", "유교", "원불교", "무교", "천도교",
                    "힌두교", "유대교", "성공회",
                ],
            },
            "marital": {
                "context": ["결혼", "혼인", "배우자"],
                "values": ["기혼", "미혼", "이혼", "사별", "별거", "동거"],
            },
            "gender": {
                "context": ["성별", "젠더"],
                "values": ["남성", "여성", "남", "여", "논바이너리", "트랜스젠더"],
            },
            "orientation": {
                "context": ["성적지향", "성지향", "성적 지향"],
                "values": ["이성애", "동성애", "양성애", "무성애", "범성애"],
            },
            "nationality": {
                "context": ["국적", "시민권", "영주권"],
                "values": [
                    "한국", "대한민국", "미국", "일본", "중국", "캐나다",
                    "영국", "호주", "독일", "프랑스",
                ],
            },
            "mental": {
                "context": ["정신건강", "정신과", "심리"],
                "values": [
                    "우울증", "불안장애", "공황장애", "강박장애",
                    "사회불안장애", "섭식장애", "PTSD", "조현병",
                ],
                "value_pattern": re.compile(
                    r'([\w가-힣]+(?:장애|증)\s*(?:치료중|약물치료|상담중|입원중))'
                ),
            },
            "school": {
                "context": ["학교", "대학교", "학교명", "출신", "재학"],
                "values": [
                    "서울대학교", "연세대학교", "고려대학교", "성균관대학교",
                    "한양대학교", "중앙대학교", "경희대학교", "건국대학교",
                    "동국대학교", "부산대학교", "충남대학교", "전남대학교",
                    "한국외국어대학교", "이화여자대학교", "숙명여자대학교",
                    "포항공과대학교", "카이스트", "KAIST",
                ],
            },
            "degree": {
                "context": ["학위", "전공", "학과"],
                "values": [],
                "value_pattern": re.compile(
                    r'([\w가-힣]+(?:학과|공학과|학부)\s*(?:학사|석사|박사|수료))'
                ),
            },
            "job_title": {
                "context": ["직위", "직급", "직책", "보직"],
                "values": [
                    "사원", "주임", "대리", "과장", "차장", "부장",
                    "이사", "상무", "전무", "부사장", "사장", "대표이사",
                    "회장", "팀장", "본부장", "실장", "센터장",
                ],
            },
            "company": {
                "context": ["재직", "근무", "회사", "직장"],
                "values": [
                    "삼성전자", "SK하이닉스", "LG전자", "현대자동차",
                    "기아", "셀트리온", "네이버", "카카오",
                    "신한금융", "KB금융", "하나금융", "우리금융",
                    "한화솔루션", "포스코", "현대중공업", "LG화학",
                ],
            },
            "dept": {
                "context": ["부서", "팀", "소속"],
                "values": [
                    "인사팀", "총무팀", "경영지원팀", "마케팅팀",
                    "영업팀", "개발팀", "연구소", "AI연구소",
                    "품질관리팀", "생산관리팀", "재무팀", "법무팀",
                    "보안팀", "IT팀", "기획팀",
                ],
            },
            "course_grade": {
                "context": ["성적", "학점", "과목"],
                "values": [],
                "value_pattern": re.compile(
                    r'(?:[\uAC00-\uD7A3]{2,})\s+([A-F][+\-]?)(?:\s|$|,)'
                ),
            },
        }

    def detect(self, text: str) -> List[PIIFinding]:
        """텍스트에서 한국어 PII를 탐지."""
        findings = []

        # 1. 정규식 패턴 매칭
        for pii_type, pattern in self.regex_patterns.items():
            for match in pattern.finditer(text):
                findings.append(PIIFinding(
                    pii_type=pii_type,
                    value=match.group(0),
                    context_keyword=f"regex:{pii_type}",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95,
                ))

        # 2. 키워드 사전 매칭
        for pii_type, config in self.keyword_dict.items():
            # 컨텍스트 키워드가 있는지 확인
            context_found = any(kw in text for kw in config["context"])

            # 구체적 값 매칭
            for val in config.get("values", []):
                if val in text:
                    findings.append(PIIFinding(
                        pii_type=pii_type,
                        value=val,
                        context_keyword=f"keyword:{val}",
                        start=text.index(val),
                        end=text.index(val) + len(val),
                        confidence=0.9 if context_found else 0.7,
                    ))

            # 값 패턴 매칭
            vp = config.get("value_pattern")
            if vp:
                for match in vp.finditer(text):
                    findings.append(PIIFinding(
                        pii_type=pii_type,
                        value=match.group(0),
                        context_keyword=f"pattern:{pii_type}",
                        start=match.start(),
                        end=match.end(),
                        confidence=0.85,
                    ))

        # 중복 제거 (같은 위치, 같은 값)
        seen = set()
        deduped = []
        for f in findings:
            key = (f.pii_type, f.value, f.start)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        return deduped

    def has_pii(self, text: str) -> bool:
        """PII가 하나라도 있으면 True."""
        return len(self.detect(text)) > 0

    def mask(self, text: str) -> str:
        """탐지된 PII를 마스킹."""
        findings = sorted(self.detect(text), key=lambda f: -f.start)
        result = text
        for f in findings:
            if f.start >= 0 and f.end > f.start:
                tag = f"<{f.pii_type.upper()}>"
                result = result[:f.start] + tag + result[f.end:]
        return result


# ═══════════════════════════════════════════════════════════
# CLI Demo
# ═══════════════════════════════════════════════════════════

def _demo():
    detector = KoreanPIIDetector()

    tests = [
        # 텍스트형 PII (기존 가드레일 우회)
        ("처방약", "하도윤 처방 아토르바스타틴 20mg 1일 2회"),
        ("알레르기", "김한결 견과류 알레르기"),
        ("진단명", "선우아 진단명 제2형 당뇨병"),
        ("수술력", "박하윤 2023.03 맹장수술 (서울대병원)"),
        ("장애", "신동현 자폐성장애 1급"),
        ("혈액형", '{"name":"임올리버","혈액형":"AB형Rh-","phone":"011-8693-7952"}'),
        ("가족", "김영진 가족: 부: 박철대(1961), 모: 최정순(1976)"),
        ("연봉", "최영희 연봉 7409만원"),
        ("퇴직금", '{"name":"김민수","퇴직금":"퇴직금 15996만원 (2023년 기준)"}'),
        ("종교", "노재훈 불교"),
        ("결혼", "오재훈 사별"),
        ("학교", "고객 조회 결과: 윤건, 학교명 연세대학교"),
        ("직위", '{"name":"홍민재","직위":"과장"}'),

        # 구조화된 토큰형 PII
        ("세션", "Session SESSION_0bd6ijhj65y2joweuyyjfyvs"),
        ("JWT", "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.kCpgMpuBq0zE8c2T5QCi7XIR4sYeyi0f4mQj"),
        ("크립토", "지갑주소 0xeb32d05e73f4461a753f587be0d61335ac006c94"),
        ("생체인식", "생체인식 ID FINGERPRINT-2024-32AE10CA"),
        ("사건번호", "사건번호 2023가합30039"),
        ("범죄기록", "황보현 2024고단9957 징역형"),
        ("GPS", "위치 37.5170°N, 129.0520°E"),
        ("정치", "고서현 ○○당 당원번호 2022-49379"),

        # 정상 텍스트 (false positive 방지 확인)
        ("정상1", "오늘 날씨가 좋습니다"),
        ("정상2", "회의는 3시에 시작합니다"),
    ]

    print("=" * 70)
    print("  Korean PII Detector v1.0 — Demo")
    print("=" * 70)

    for label, text in tests:
        findings = detector.detect(text)
        status = f"🔴 {len(findings)}건" if findings else "✅ clean"
        print(f"\n[{label}] {status}")
        print(f"  TEXT: {text[:80]}")
        for f in findings:
            print(f"  → {f.pii_type:15s} | {f.value[:50]:50s} | {f.context_keyword}")


if __name__ == "__main__":
    _demo()

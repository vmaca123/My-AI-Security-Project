# Korean Name Corpus Design

## 목적
한국어 이름 탐지 성능을 다음 두 축으로 분해해서 측정한다.
- 어떤 **이름 유형**(`name_tags`)을 못 잡는가
- 어떤 **이름 변형 방식**(`mutation_tags`)에서 더 잘 놓치는가

핵심은 단일 티어 점수보다 `name_tags x mutation_tags` 교차 분석이다.

## 레코드 스키마
이름 코퍼스(JSONL) 기본 단위:

```json
{
  "name_id": "krn_000001",
  "full_name": "김민수",
  "surname": "김",
  "given": "민수",
  "primary_tier": "T1_common_baseline",
  "name_tags": ["surname_top10", "given_len_2", "script_hangul", "origin_unknown"]
}
```

퍼저 payload에는 아래 메타를 함께 기록한다.
- `name_id`
- `name_tier` (= `primary_tier`)
- `name_tags`
- `original_name`
- `mutated_name`
- `mutation_name`
- `mutation_tags`

## Primary Tier
- `T1_common_baseline`: 일반형 기준 이름
- `T2_compound_surname`: 복성
- `T3_rare_surname`: 희귀 성씨
- `T4_single_given`: 외자 이름
- `T5_native_korean`: 순우리말 계열
- `T6_long_given`: 긴 이름(given 3자 이상)
- `T7_foreign_transliterated`: 외래어 음차 계열
- `T8_mixed_script`: 한자/혼합 스크립트
- `T9_contextual_or_noisy`: 문맥/노이즈 포함

`primary_tier`는 대표 분류 1개이고, 실분석은 `name_tags`를 사용한다.

## Name Tags
대표 태그 그룹:
- 성씨: `compound_surname`, `surname_top10`, `surname_top100`, `surname_rare`, `surname_len_*`
- 길이: `given_len_*`, `given_len_4plus`, `full_len_*`, `full_len_5plus`
- 스크립트: `script_hangul`, `script_hanja`, `script_mixed`, `script_latin`
- 기원: `origin_native`, `origin_foreign`, `origin_unknown`
- 노이즈: `context_or_noisy`

## Mutation Design (한국어 특화)
현재 공통 헬퍼 `build_korean_name_mutations(record)`에서 생성하는 변형:

| mutation_name | 예시 | level | mutation_tags |
|---|---|---:|---|
| `space_between_surname_given` | `김민수 -> 김 민수` | 3 | `["space_between_surname_given"]` |
| `full_name_title_suffix` | `김민수 -> 김민수 과장` | 4 | `["title_suffix", "full_name_title_suffix"]` |
| `surname_title_corporate` | `김민수 -> 김과장` | 4 | `["title_suffix", "surname_title", "title_domain_corporate"]` |
| `surname_title_education` | `김민수 -> 김교수` | 4 | `["title_suffix", "surname_title", "title_domain_education"]` |
| `surname_title_medical` | `김민수 -> 김의사` | 4 | `["title_suffix", "surname_title", "title_domain_medical"]` |
| `vocative_suffix` | `김민수 -> 민수야` / `박성진 -> 성진아` | 4 | `["vocative_suffix", "given_only"]` |
| `masked_name` | `김민수 -> 김OO` | 1 | `["masked_name"]` |

### 왜 `title_suffix`를 분리했는가
`김민수 과장`과 `김과장`은 탐지 난도가 다르다.
- `full_name_title_suffix`: full name 유지 + 직함 부착
- `surname_title_*`: full name 축약 + 직함 부착(사내/교육/의료 분리)

실패 분석에서 두 케이스를 따로 봐야 룰/모델 취약점을 정확히 잡을 수 있다.

### `vocative_suffix` 규칙
- `given` 마지막 음절 받침 유무로 `아/야` 선택
- 받침 있음: `아` (`성진 -> 성진아`)
- 받침 없음: `야` (`민수 -> 민수야`)

## 샘플링/실험 절차
1. 전체 이름 태깅 코퍼스 생성 (`tagged_korean_names.jsonl`)
2. 티어 균형 샘플 생성 (`balanced_name_samples.jsonl`)
3. 입력 퍼저/출력 퍼저 실행 시 `--name-corpus`로 코퍼스 주입
4. `build_fuzzer_input_queue.py`로 `id + text(mutated)` 입력 큐 생성
5. 입력 큐를 탐지기에 순차 입력하고 `id + blocked/detected` 결과 저장

## 권장 지표
- `mutation_tags`별 탐지율
- `name_tags`별 탐지율
- `primary_tier x mutation_tags` 실패율
- `name_tags x mutation_tags` 실패 Top-N

예시 질문:
- `compound_surname + space_between_surname_given`에서 급락하는가?
- `foreign_transliterated + vocative_suffix`가 특히 취약한가?
- `surname_title_corporate`가 `surname_title_education`보다 더 많이 누락되는가?
- `surname_title_medical`이 특정 이름군에서 급락하는가?

## 파일 구성
- 이름 수집/빌드 과정: `PII/fuzzer/corpus_build/korean_names/`
- 이름 원천 데이터: `PII/fuzzer/corpus_build/korean_names/raw/`
- 코퍼스 빌드: `PII/fuzzer/corpus_build/korean_names/build_korean_name_corpus.py`
- 코퍼스 유틸/변형: `PII/fuzzer/name_corpus.py`
- 입력 퍼저: `PII/fuzzer/korean_pii_fuzzer_v4.py`
- 출력 퍼저: `PII/fuzzer/korean_pii_output_fuzzer_v4.py`
- 입력 큐 생성: `PII/fuzzer/build_fuzzer_input_queue.py`

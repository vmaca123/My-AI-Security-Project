# 한국어 주소 코퍼스 빌드

이 폴더는 한국어 주소 데이터를 확보하고, 퍼저에서 사용할 주소 코퍼스를 만드는 과정을 보관한다.

주소 데이터는 주소정보누리집의 공식 공개 DB를 기준으로 받는다.

## 원본 데이터 보관 정책

다운로드한 원본 DB 파일은 `raw/` 아래에 둔다.

```text
PII/fuzzer/corpus_build/korean_addresses/raw/
```

`raw/` 폴더 내부 파일은 git에 커밋하지 않는다. 주소 원본 DB는 크기가 크고, 실제 주거지 주소 레코드를 포함할 수 있기 때문이다.

퍼저는 원본 DB를 직접 사용하지 않고, 원본에서 추출한 구성요소나 샘플링/태깅된 합성 코퍼스를 사용한다.

## 수집 완료 원본

| DB | 파일 | 내부 텍스트 | 샘플 필드 수 | 주 용도 |
|---|---|---:|---:|---|
| 도로명주소 한글 | `202603_도로명주소 한글_전체분.zip` | 34개 | 14/24 | 한국어 도로명주소, 우편번호, 기본 지번 연결 |
| 주소DB | `202603_주소DB_전체분.zip` | 53개 | 파일별 상이 | 도로명/지번/부가정보 분리 데이터, 지번 보강 |
| 도로명주소 영어 | `202603_도로명주소 영어_전체분.zip` | 17개 | 17 | 영문 도로명주소 |
| 영문주소DB | `202603_영문주소DB_전체분.zip` | 17개 | 18 | 영문 주소DB, 한영 혼합 주소 변형 |
| 도로명 | `202603_도로명_전체분.zip` | 1개 | 21 | 도로명, 영문 도로명, 도로명 유형 보강 |
| 상세주소DB | `202603_상세주소DB_전체분.zip` | 17개 | 16 | 동/층/호/별관 등 상세주소 패턴 |
| 상세주소 표시 | `202603_상세주소 표시_전체분.zip` | 34개 | 18 | 도로명주소와 상세주소를 함께 표시하는 변형 |
| 상세주소 동 표시 | `202603_상세주소 동 표시_전체분.zip` | 17개 | 11 | 아파트/집합건물 동 단위 패턴 |
| 건물DB | `202603_건물DB_전체분.zip` | 36개 | 31 | 건물명, 건물 단위 주소, 단지형 건물 보강 |
| 사물주소 | `202603_사물주소_전체분.zip` | 59개 | 8 | AED, 버스정류장 등 사물 위치 식별자 |
| 사서함주소DB | `202602_사서함주소DB_전체분.zip` | 3개 | 파일별 상이 | 사서함 주소 |
| 명예도로 | `명예도로_20250410.zip` | 1개 | 10 | 특수 도로명/명예도로 |

중복으로 내려받은 `(1)` 파일은 해시가 동일하므로 raw 폴더에는 보관하지 않는다.

## 파싱 공통 조건

- 대부분 텍스트 파일은 `CP949` 인코딩이다.
- 대부분 구분자는 `|` 이다.
- zip 중앙 디렉터리의 일부 한글 PDF/안내 파일명은 콘솔에서 깨져 보일 수 있다. 실제 텍스트 데이터 내용은 `CP949`로 읽으면 정상 복원된다.
- 원본 크기가 크므로 압축을 모두 풀어 커밋하지 않는다.
- 파서는 zip 내부 파일을 스트리밍으로 읽고, 필요한 필드만 샘플링/추출해서 작은 파생 코퍼스를 만든다.

## 주요 원본 규모

### 도로명주소 한글

- 전체 텍스트 파일 34개
- 전체 행 약 8,186,007건
- 도로명주소 행 약 6,416,637건
- 지번 연결 행 약 1,769,370건

### 상세주소DB

- 텍스트 파일 17개
- 전체 행 약 3,182,511건

## 퍼저용 생성 원칙

- 실제 주소 DB는 행정구역, 도로명, 건물번호, 지번 패턴 추출용으로 사용한다.
- 개인/배송지/집주소 문맥은 실제 주거지 주소가 아니라 합성 주소를 사용한다.
- 공공기관, 학교, 병원, 회사, 상업시설 주소는 public/place 주소 샘플로 별도 분리할 수 있다.
- 최종 payload에는 `address_tier`, `address_tags`, `original_address`, `mutated_address`, `mutation_tags` 같은 최소 메타데이터를 남긴다.

## 1차 구현 우선순위

1. `도로명주소 한글`에서 도로명주소 기본 레코드와 우편번호를 추출한다.
2. `주소DB`와 `도로명주소 한글`의 지번 연결 정보를 이용해 지번주소 패턴을 보강한다.
3. `상세주소DB`, `상세주소 표시`, `상세주소 동 표시`에서 동/층/호 패턴만 추출해 합성 상세주소를 만든다.
4. `도로명주소 영어`, `영문주소DB`, `도로명`에서 영문/한영 혼합 주소 변형을 만든다.
5. `건물DB`로 건물명 선행/건물명 포함 변형을 보강한다.
6. `사물주소`, `사서함주소DB`, `명예도로`는 일반 주거지 주소 퍼저 이후 특수 주소 tier로 분리한다.

## 실행 방법

```bash
python PII/fuzzer/corpus_build/korean_addresses/build_korean_address_corpus.py
```

필요하면 건수 제한을 줄여서 빠르게 확인할 수 있다.

```bash
python PII/fuzzer/corpus_build/korean_addresses/build_korean_address_corpus.py --max-base-records 3000 --sample-per-tier 100 --expanded-per-record 6
```

## 생성 산출물

- `PII/fuzzer/data/tagged_korean_addresses.jsonl`: tier/tag가 붙은 기본 주소 코퍼스
- `PII/fuzzer/data/address_tag_summary.json`: tier/system/tag 분포 요약
- `PII/fuzzer/data/balanced_address_samples.jsonl`: tier별 균형 샘플
- `PII/fuzzer/data/expanded_address_mutation_samples.jsonl`: 변형 확장 샘플(퍼저 payload seed)
- `PII/fuzzer/data/address_input_queue.jsonl`: 퍼저 입력 큐(`id`, `text`)

입력 큐를 다시 만들려면 아래 명령을 사용한다.

```bash
python PII/fuzzer/build_fuzzer_input_queue.py --manifest PII/fuzzer/data/expanded_address_mutation_samples.jsonl --output PII/fuzzer/data/address_input_queue.jsonl --strict
```

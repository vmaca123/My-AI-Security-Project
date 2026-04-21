# Layer 1 — Microsoft Presidio (regex/NER-based PII)

LLM Gateway의 첫 번째 방어선. Microsoft Presidio를 `pre_call` 모드로 실행하여 영어/한국어 PII를 정규식 + NER로 탐지·마스킹.

## 역할

- **주요 PII 타입**: US_SSN, CREDIT_CARD, EMAIL_ADDRESS, PHONE_NUMBER, PERSON, LOCATION, DATE_TIME, NRP, IBAN, CRYPTO, AWS_ACCESS_KEY, US_DRIVER_LICENSE 등 30+ 국제 PII entity
- **언어 설정**: `presidio_language: "en"` (영어 우세) — 한국어는 부분적으로 매칭됨
- **동작 모드**: `filter_scope: "both"`, `run_on: "both"` — request/response 양방향 마스킹
- **자체 호스팅**: Docker 컨테이너 `presidio-analyzer` + `presidio-anonymizer`

## LiteLLM 등록 (config.yaml)

```yaml
- guardrail_name: "Presidio PII"
  litellm_params:
    guardrail: presidio
    mode: "pre_call"
    guardrail_info:
      presidio_analyzer_api_base: "http://presidio-analyzer:3000"
      presidio_anonymizer_api_base: "http://presidio-anonymizer:3000"
      presidio_language: "en"
      output_parse_pii: true
      filter_scope: "both"
      run_on: "both"
      pii_entities_config:
        CREDIT_CARD: {action: "MASK"}
        US_SSN: {action: "MASK"}
        EMAIL_ADDRESS: {action: "MASK"}
        PHONE_NUMBER: {action: "MASK"}
        # ... (30+ entities)
```

## 측정 성능 (10k stratified 평가 기준)

| 지표 | 값 |
|---|---:|
| Any-change rate | 69.49% |
| True neutralize rate | 50.19% |
| Avg latency | 72ms |
| Errors | 0 |

- **영어 PII**: 거의 완벽 (US_SSN, EN_phone, EN_email 99%+)
- **한국어 PII**: 부분 탐지. 체크섬/포맷형은 상당 부분 잡음, 텍스트형(알레르기/처방/법률 등)은 대부분 놓침
- **보완층**: Layer 0 (한국어 정규화+사전) 또는 Layer 4 (LLM judge)가 Presidio 공백을 메움

## 저장된 평가 결과

| 파일 | 설명 |
|---|---|
| `results_L1_1000.json` | Presidio 1000건 input 평가 결과 |
| `results_L1_INPUT_1000_BLOCK.json` | 입력 단계 BLOCK된 케이스 |
| `results_L1_OUTPUT_1000.json` | 출력 단계 평가 결과 |

## 한계

1. `presidio_language: "en"` → 한국어 전용 recognizer(KR_RRN 등) 비활성화 상태
2. 한국어 텍스트형 PII(진단명/처방/가족관계 등)는 Presidio NER로도 탐지 어려움
3. 한국어 이름을 PERSON으로 잡긴 하지만 변이(자모분해/한자/emoji) 적용 시 놓침

→ Layer 0에서 한국어 정규화 후 Presidio에 전달하면 회복됨.

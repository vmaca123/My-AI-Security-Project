# Layer 3 — Lakera Guard v2

LLM Gateway의 세 번째 방어선. Lakera의 **프롬프트 인젝션 + PII 통합 탐지** 서비스를 `pre_call` 모드로 실행.

## 역할

- **엔진**: Lakera Guard v2 (`https://api.lakera.ai`)
- **주 탐지 대상**: **프롬프트 인젝션 / 탈옥 시도** — PII 탐지는 보조
- **동작**: `pre_call` — LLM 호출 전 입력 스캔

## LiteLLM 등록 (config.yaml)

```yaml
- guardrail_name: "Lakera"
  litellm_params:
    guardrail: lakera_v2
    mode: "pre_call"
    api_base: "https://api.lakera.ai"
    project_id: "admin"
  environment_variables:
    LAKERA_API_KEY: os.environ/LAKERA_API_KEY
```

## 측정 성능 (10k stratified 평가 기준)

| 지표 | 값 |
|---|---:|
| Any-change rate | **0.0%** |
| True neutralize rate | **0.0%** |
| Avg latency | 7ms |
| Errors | 0 |

**→ 10,000건 중 한 건도 PII 탐지로 차단하지 않음.** 이는 **인프라 장애가 아니라 정상 동작**임:

1. Lakera는 **인젝션 탐지 전용** — 단순 PII가 포함된 평문 텍스트는 공격으로 보지 않음
2. 4/16, 4/19 두 번의 독립 평가에서 일관되게 0% catch 확인
3. API 호출은 정상 (avg 7ms, errors 0)
4. 본 연구의 퍼저 페이로드는 "PII 포함 일반 문장" 위주라 Lakera의 threat model 밖

## 실무 시사점

- **Lakera를 PII 방어선으로 기대하지 말 것** — 인젝션/탈옥 공격 전용 레이어
- **Presidio + Bedrock + Layer 0** 조합이 실제 PII 방어를 담당
- Lakera는 별도 공격 시나리오 (prompt injection, jailbreak) 에서 별도 평가 필요
  - 예: `PII + Injection` 결합 공격을 다뤄야 Lakera 효과 측정 가능

## 앞으로의 평가 방향

1. Injection 공격 payload 별도 생성 (HouYi 등) → Lakera 탐지율 측정
2. PII + Injection 결합 공격 → 레이어별 방어 효과 분리 측정
3. Lakera payload 옵션(regex 매치 위치 반환)으로 진짜 threat score 분석

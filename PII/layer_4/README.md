# Layer 4 — GPT-4o Judge (LLM-as-Judge)

최종 방어선. GPT-4o-mini로 자연어 맥락 기반 PII 탐지. `post_call` 모드.

## 역할

- **엔진**: OpenAI GPT-4o-mini (zero-shot classification prompt)
- **설정**:
  - `PII_JUDGE_MODEL=gpt-4o-mini`
  - `PII_JUDGE_THRESHOLD=0.7` (confidence 0.7 이상이면 BLOCK)
  - `PII_JUDGE_MAX_TOKENS=1000`
- **동작**: `post_call` — LLM 응답 생성 후 최종 검증
- **강점**: 자연어 맥락 이해 — Presidio/Bedrock이 놓친 PII를 LLM이 추론으로 잡음
- **약점**: 비용 + 지연 (~2,200ms/건, $0.0001/건)

## LiteLLM 등록 (config.yaml)

```yaml
- guardrail_name: "gpt4o-pii-judge"
  litellm_params:
    guardrail: custom_guardrail.GPT4oPIIJudge
    mode: "post_call"
```

## Cascade 최적화 (실험 시)

**모든 케이스에 L4를 호출하면 비용/시간 폭발** — 실무에서는 cascade 적용:

1. L1~L3가 이미 잡은 케이스(TRUE) → L4 스킵
2. L1~L3가 놓친 케이스(BYPASS) 또는 부분만 잡은 케이스(FALSE) → L4 호출
3. 약 20% 케이스만 L4 투입 → 비용 80% 절감

평가 스크립트(`cascade_evaluator.py`)는 이 cascade 로직을 구현하되, `--all` 플래그로 공정 비교를 위해 전 케이스 L4 호출도 가능.

## 측정 성능 (10k 풀 평가 기준)

| Config | TRUE detection | 증가분 |
|---|---:|---:|
| Baseline (L1~L3) | 80.15% | — |
| **Baseline + L4** | **90.96%** | **+10.81%p** |
| KR_semantic slice (Baseline + L4) | 87.40% | +37.78%p vs A |

## Layer 0 vs L4 head-to-head

1만건 평가에서 **Layer 0(한국어 정규화, LLM 없음)가 GPT-4o judge를 능가**:

| Config | Overall TRUE | KR_semantic TRUE | Latency/건 | 비용/건 |
|---|---:|---:|---:|---:|
| Baseline + L4 (LLM judge) | 90.96% | 87.40% | ~2,200ms | ~$0.0001 |
| **With L0 (no LLM)** | **94.32%** | **96.39%** | ~540ms | $0 |
| **Full (L0+L4)** | **97.23%** | **98.85%** | ~2,700ms | ~$0.0001 |

→ 한국어 텍스트형 PII에서 Layer 0가 L4보다 **+8.99%p 더 잘 잡으면서 220배 빠르고 무료**.

## 운영 주의

1. **OpenAI API 키 필수** (`OPENAI_API_KEY`)
2. **Rate limit 주의**: gpt-4o-mini tier별 RPM 다름. 평가 스크립트는 `--concurrency` 옵션으로 동시 호출 제어.
3. **Threshold 튜닝**: 0.7이 default지만, recall 우선이면 낮추고 precision 우선이면 높임.
4. **Cost 제어**: 프로덕션에서는 cascade 필수. 모든 케이스에 L4 호출하면 월간 LLM 비용 > 기반 LLM 비용.

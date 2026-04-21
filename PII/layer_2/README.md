# Layer 2 — AWS Bedrock Guardrails

LLM Gateway의 두 번째 방어선. AWS 관리형 가드레일을 `during_call` 모드로 병렬 실행.

## 역할

- **엔진**: AWS Bedrock Guardrails (`bedrock-runtime.us-east-1.amazonaws.com`)
- **탐지 대상**: 50+ PII entity + 콘텐츠 필터링 + 토픽 제한 + 문맥 기반 그라운딩
- **동작**: `mask_request_content + mask_response_content` 양방향 마스킹
- **장점**: Presidio가 놓치는 한국어/다국어 PII도 ML 기반으로 상당수 포착

## LiteLLM 등록 (config.yaml)

```yaml
- guardrail_name: "Bedrock Guardrail"
  litellm_params:
    guardrail: bedrock
    mode: "during_call"
    guardrailIdentifier: "lwkm339ab127"   # ← litellm_params 직접 아래 (guardrail_info 안이면 v4.69+에서 None으로 읽혀서 400 에러)
    guardrailVersion: "DRAFT"
    default_on: true
```

**⚠️ 중요 주의**: LiteLLM v4.69+ 에서 config 스키마 변경. `guardrailIdentifier`/`guardrailVersion`을 `guardrail_info` 안에 넣으면 `initialize_bedrock`이 `litellm_params.guardrailIdentifier`를 직접 읽기 때문에 `None`으로 처리되어 `https://.../guardrail/None/version/None/apply` 호출 → `400 Guardrail was enabled but input is in incorrect format` 에러. 반드시 `litellm_params` 직접 아래로.

## 측정 성능 (10k stratified 평가 기준)

| 지표 | 값 |
|---|---:|
| Any-change rate | 79.18% |
| True neutralize rate | 62.12% |
| Avg latency | 474ms |
| Errors | 0 (config 패치 후) |

- Bedrock은 Presidio보다 한국어 텍스트형 PII를 더 잘 잡는 경향
- 하지만 한국어 semantic PII(알레르기/처방 등)에서는 여전히 50%대 탐지
- Latency가 가장 큼 (~500ms) — 네트워크 왕복 포함

## 저장된 평가 결과

| 파일 | 설명 |
|---|---|
| `results_L2_INPUT_1000.json` | Bedrock 1000건 input 평가 결과 |
| `results_litellm_L2_test100.json` | LiteLLM 통합 100건 smoke test |

## 운영 주의

1. **AWS 자격증명**: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (또는 profile) 환경변수 필수
2. **Region**: `us-east-1` (가드레일 생성 region과 일치)
3. **Policy 변경**: Bedrock 콘솔에서 정책 수정 시 즉시 반영됨 — 재평가 시 이전 결과와 다를 수 있음
4. **정책 버전**: `DRAFT` 버전은 덮어쓰기 가능. 프로덕션은 버전 고정 권장.

## 실험 중 발견한 이슈

1. **정책 변경 감지**: 4/16 → 4/19 사이 Bedrock 응답 패턴 변경 (MASK → BLOCK 증가)
2. **LiteLLM 호환성 깨짐**: `image: main-latest` 컨테이너 재시작 시 config 스키마 변경 → 위 config 패치 필요

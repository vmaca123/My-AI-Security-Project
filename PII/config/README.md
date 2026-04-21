# Runtime Configuration

LiteLLM Gateway + Presidio containers 구동용 설정.

## config.yaml

LiteLLM proxy에 5계층 가드레일(L0~L4) 등록. 주요 섹션:

```yaml
guardrails:
  - guardrail_name: "korean-layer0"
    litellm_params:
      guardrail: korean_layer0_guardrail.KoreanLayer0Guard
      mode: "pre_call"

  - guardrail_name: "Presidio PII"
    litellm_params:
      guardrail: presidio
      mode: "pre_call"
      guardrail_info:
        presidio_analyzer_api_base: "http://presidio-analyzer:3000"
        presidio_language: "en"
        pii_entities_config: {...}  # 30+ entities

  - guardrail_name: "Bedrock Guardrail"
    litellm_params:
      guardrail: bedrock
      mode: "during_call"
      guardrailIdentifier: "..."     # ← litellm_params 직접 아래 (v4.69+ 호환)
      guardrailVersion: "DRAFT"
      default_on: true

  - guardrail_name: "Lakera"
    litellm_params:
      guardrail: lakera_v2
      mode: "pre_call"

  - guardrail_name: "gpt4o-pii-judge"
    litellm_params:
      guardrail: custom_guardrail.GPT4oPIIJudge
      mode: "post_call"
```

### Bedrock config 주의

LiteLLM v4.69+ 에서 `guardrailIdentifier`/`guardrailVersion`은 **`litellm_params` 직접 아래**에 있어야 함. `guardrail_info` 안에 넣으면 `initialize_bedrock`이 `None`으로 읽어서 `400 Guardrail was enabled but input is in incorrect format` 에러 발생.

## docker-compose.yml

```yaml
services:
  db:            # PostgreSQL (LiteLLM 메타데이터)
  litellm:      # Gateway proxy (port 4000)
```

Presidio는 별도 컨테이너(`presidio-analyzer`, `presidio-anonymizer`)로 실행. 필요한 환경변수:

```
OPENAI_API_KEY         # L4 judge용
AWS_ACCESS_KEY_ID      # L2 Bedrock용
AWS_SECRET_ACCESS_KEY
AWS_REGION
BEDROCK_GUARDRAIL_ID
LAKERA_API_KEY         # L3용
PII_JUDGE_MODEL=gpt-4o-mini
PII_JUDGE_THRESHOLD=0.7
```

## 실행 방법

```bash
# .env 파일 생성 (위 변수 채움) — NEVER commit!
docker compose up -d
docker start presidio-analyzer presidio-anonymizer
curl http://localhost:4000/health/liveness  # → "I'm alive!"
```

## Layer 0 배포

Layer 0는 LiteLLM 컨테이너 안에 Python 모듈로 배포:

```bash
docker cp ../layer_0/korean_normalizer.py litellm-litellm-1:/app/
docker cp ../layer_0/korean_pii_detector.py litellm-litellm-1:/app/
docker cp ../layer_0/korean_layer0_guardrail.py litellm-litellm-1:/app/
docker cp config.yaml litellm-litellm-1:/app/config.yaml
docker compose restart litellm
```

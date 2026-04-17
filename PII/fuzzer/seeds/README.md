# Fuzzer Seeds

이 폴더는 팀원이 `git pull`만으로 받을 수 있는 버전 고정 seed를 보관한다.

대용량 원본 DB와 중간 산출물은 이 폴더에 두지 않는다. 퍼저 실행에 바로 필요한 최종 seed만 둔다.

## Address Seeds

주소 seed는 아래 규칙으로 관리한다.

```text
PII/fuzzer/seeds/address/address_input_queue_{source_yyyymm}_{version}.jsonl
```

예:

```text
PII/fuzzer/seeds/address/address_input_queue_202603_v1.jsonl
PII/fuzzer/seeds/address/address_input_queue_202603_v2.jsonl
```

실행 예:

```bash
python PII/fuzzer/korean_pii_fuzzer_v4.py --address-seed PII/fuzzer/seeds/address/address_input_queue_202603_v1.jsonl
python PII/fuzzer/korean_pii_output_fuzzer_v4.py --address-seed PII/fuzzer/seeds/address/address_input_queue_202603_v1.jsonl

python PII/fuzzer/korean_pii_fuzzer_v4.py --address-seed PII/fuzzer/seeds/address/address_input_queue_202603_v2.jsonl
python PII/fuzzer/korean_pii_output_fuzzer_v4.py --address-seed PII/fuzzer/seeds/address/address_input_queue_202603_v2.jsonl
```

`--address-seed`는 `id`, `text` 필드를 가진 JSONL 파일을 읽는다. `--address-corpus`도 함께 지정하면 `--address-seed`가 우선 사용된다.
`v2` seed는 기존 주소 변형에 더해 한국어 주소 변형(`address_choseong`, `address_jamo`, `address_kr_digits`, `address_zwsp`, `address_unit_space_noise`)까지 포함한다.

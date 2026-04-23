# CHANGELOG — 한국어 PII 가드레일 프로젝트

> 이 파일은 **누적 기록**이다. 절대 덮어쓰지 않고 새 항목만 위에 추가한다.
> 콘테스트/캡스톤 발표 자료 작성 시 어떤 commit이 어떤 의미였는지 추적용.

---

## 📅 2026-04-22 (수) — Phase 5: 발표·문서 패키징

| 시간 | Commit | 의미 |
|---|---|---|
| 00:02 | `d9b9e1d` | **DOCX 패키징** — 정연서(팀원) 요청으로 PPT 작성용 자료 Word로 export |

### 산출물
- `paper/결과요약_for_PPT.docx` (420KB, fig11+fig13 embed, 5~6p) ★ PPT용
- `paper/캡스톤논문_전체_v1.docx` (55KB, 24p 전체 논문)
- `paper/build_docx.py` — 재생성 가능한 빌더

### 메모
- 정연서: "ppt에 쓸 자료 깃헙 말고 pdf나 word로 보내줘 그게 더 정리하기 쉬울 거 같음"
- 의사결정: Word 우선 (편집 가능, copy-paste 편함). PDF는 추후 필요 시 LibreOffice/Word로 변환

---

## 📅 2026-04-21 (화) — Phase 1~4 집중 작업일 (대 마라톤)

이 날 하루에 **15개 commit, 4개 phase 모두 완료**. 새벽까지 진행.

### Phase 5 (논문 작성)
| 시간 | Commit | 의미 |
|---|---|---|
| 늦은 시간 | `3e99195` | **논문 본문 v1** — 348라인, 학술지 스타일 산문 (paper/capstone_main_v1.md) |
| 그 전 | `176de26` | **논문 초안 v1** — 475라인, outline+수치 형식 (paper/capstone_draft_v1.md) |

### Phase 2 — Validity-First Fuzzer Robustness
| 시간 | Commit | 의미 |
|---|---|---|
| 저녁 | `6550a54` | **Phase 2 완료** — v4 fuzzer 4-way 재평가. Layer 0 우위 +3.36→+4.56%p로 확대 입증 |
| 저녁 | `1336682` | (merge) 팀원 작업과 동기화 |
| 오후 | `4ab493c` | Phase 2 부분 + fig13 ablation viz + README index 업데이트 |

**v4 평가 결과:**
- A Baseline: 80.15% → 80.11% (-0.04%p)
- C +Layer 0: 94.32% → **94.99%** (+0.67%p)
- B vs C: +3.36%p → **+4.56%p** (Layer 0 우위 확대)
- KR_semantic L0 vs LLM: +8.99%p → **+10.65%p**
- 결론: "방어 메커니즘의 속성, 퍼저 구현의 artifact 아님"

### Phase 4 — Reproducibility & Packaging
| 시간 | Commit | 의미 |
|---|---|---|
| | `10e68d6` | **Makefile + scripts/run_eval_pipeline.sh + HF dataset card + PPTX v5** — 단일 명령 재현 |
| | `de1181b` | **89개 pytest unit test + GitHub Actions CI** (Python 3.11+3.12 matrix) |

### Phase 3 — Ablation & Smart Cascade
| 시간 | Commit | 의미 |
|---|---|---|
| | `d5ace11` | **Layer 0 Ablation** (Dict 96% 기여) + **L4 Smart Skip** (94% 호출 절감) |

**핵심 발견:**
- Layer 0 효과의 **96%는 키워드 사전**, 정규화는 0.31%p (보조 역할)
- L0+L1~L3가 94.32% 케이스 처리 → L4는 5.68%만 → **호출 94% 절감, detection 동일**

### Phase 1 — Academic Quality
| 시간 | Commit | 의미 |
|---|---|---|
| | `ff02357` | **Latency p99 + McNemar test (p<1e-28) + FP test (98% clean)** |

**핵심 발견:**
- L0 추가 latency: +52ms mean / +135ms p99 (사실상 공짜)
- L0 vs LLM judge: McNemar **p < 2e-28** (결정적 유의)
- 정상 한국어 문서 50건 FP: 26% → 2% (짧은 키워드 컨텍스트 필수 규칙으로 수정)

### 평가 인프라 + 결과 + 설정 + README
| 시간 | Commit | 의미 |
|---|---|---|
| | `a81044c` | **evaluation/ 13 스크립트 + results/ + config/ + 루트 README** 풀 패키징 |
| | `6b8185f` | **Layer 0 detector v2 보강** (P0/P1: medical_rec, emp_id, plate, parcel...) + layer_1~4 README |
| | `0cc9da1` | **Layer 0 초기 추가** (Korean Normalizer + Detector + LiteLLM Guardrail wrapper) |

### 팀원 작업 정리 (이전 작업 cleanup)
| 시간 | Commit | 의미 |
|---|---|---|
| | `30efb7f` | final_fuzzer 디렉토리 삭제 (PII/fuzzer로 통합) |
| | `ef7af60` | prompt_injection 디렉토리 삭제 (이번 콘테스트 범위 외) |
| | `bea5b0b` | toxicity 디렉토리 삭제 (이번 콘테스트 범위 외) |

### 팀원 v4 퍼저 작업
| 시간 | Commit | 의미 |
|---|---|---|
| | `5a4975a` | "의료기록번호" — 팀원 추가 작업 |
| | `d1dc0b5` | 거래내역 생성기 보강 (transaction_korean mutations 13종) |
| | `c4ca51d` | 처방전 semantic generator 보강 (22 약품 × dose×freq×route table) |
| | `d17be7f` | 한국어 개인정보 출력 퍼저에 계정 생성/검증 추가 |
| | `fb84ef9` | PII rule quality checklist 추가 (P0/P1/P2 우선순위) |

---

## 📅 2026-04-17 (목) — 팀원 corpus 확장

| 시간 | Commit | 의미 |
|---|---|---|
| | `1af92fb` | address-seed 사용 시 seed 기반 변이 재생성 |
| | `4855809` | 큰 데이터 git 분할 |
| | `2c4b976` | 이름도 seed로 저장 |
| | `ad9178c` | 깨끗한 주소 생성 + 한국어 변형 저장 |
| | `9001baf` | seed 기반 입력 큐 |
| | `3d7f28a` | .gitignore에 큰 생성물 제외 |

---

## 📅 2026-04-16 (수) — 팀원 이름 코퍼스 설계

| 시간 | Commit | 의미 |
|---|---|---|
| | `83b9e58` | 한국어 이름 코퍼스 설계 문서 추가 |
| | `6bb65b4` | 한국어 이름 코퍼스 + PII v4 생성 흐름 정리 |

---

## 📅 2026-04-09~13 — 초기 fuzzer/이름 데이터 수집

| 날짜 | Commit | 의미 |
|---|---|---|
| 04-13 | `7feec4b`, `078fdcb` | 한국 이름 08년도 이후 수집 + 성 추출 |
| 04-10 | `bd258df`~`5d7938a` | 파일 4개 업로드 |
| 04-09 | `bc4b279`~`d7eb3f2` | fuzzer.json, 초기 셋업 |

---

## 📅 2026-04-08 (수) — 프로젝트 초기 셋업

| 시간 | Commit | 의미 |
|---|---|---|
| | `8fa40ca` | Claude AI code review & security review workflows 추가 |
| | `03ffcd3` | fuzzer 디렉토리, final_fuzzer 구조 추가 |

---

## 📅 2026-04-03 (목) — 레포 초기 생성

| 시간 | Commit | 의미 |
|---|---|---|
| | `8134049` | **Initial commit** — 보안 테스트 프레임워크 폴더 구조 (Prompt Injection / PII / Toxicity) |

---

# 🏆 핵심 마일스톤 요약 (역사적 시점)

## M1. 프로젝트 시작 (2026-04-03)
- 보안 테스트 3개 영역 (Prompt Injection / PII / Toxicity) 프레임워크 셋업

## M2. v4 Validity-First Fuzzer 완성 (2026-04-09 ~ 04-21)
- 91종 PII × 6 변이 레벨 × validity-first 시드 생성
- 팀원 작업: prescription/account/transaction 전용 generator + 21개 한국어 전용 변이
- 이름 코퍼스 85,961건 + 주소 코퍼스 50,000건 tagged

## M3. Layer 0 설계 + 통합 (2026-04-21 새벽)
- 13단계 한국어 정규화 + 42 정규식 + 22 키워드 사전
- LiteLLM `CustomGuardrail` 인터페이스 구현
- Bedrock config 스키마 변경 이슈 발견·해결 (LiteLLM v4.69+)

## M4. 4-way 평가 완료 (2026-04-21)
- 10,000건 stratified payloads 진짜 API 호출
- A/B/C/D 4 configs 비교
- **C가 B를 +8.99%p 능가 (KR_semantic)**
- McNemar p < 1e-28 통계 유의

## M5. Phase 1~4 학술 품질 확보 (2026-04-21)
- Phase 1: latency p99, McNemar, FP 측정
- Phase 2: v4 robustness 재평가 (우위 확대 입증)
- Phase 3: ablation (Dict 96%) + smart cascade (94% 비용 절감)
- Phase 4: CI 89 tests + Makefile + HF dataset + PPTX v5

## M6. 논문 + 패키징 (2026-04-21~22)
- 논문 본문 v1 (348라인 학술 산문)
- 결과 요약 DOCX (PPT 작성용) + 전체 논문 DOCX
- README Research Outcomes Index

---

# 📊 데이터 보존 — 평가 결과 timeline

## 1차 평가 (2026-04-21 오후)
- `eval_10k_l1l3.json` — A Baseline 결과 (14MB)
- `eval_10k_l0_l1l3.json` — C With L0 결과 (17MB)
- `eval_10k_l1l4_full.json` — B Baseline+L4 결과 (11MB)
- `eval_10k_l0_l1l4_full.json` — D Full 결과 (13MB, L4 결과 merge)

## 2차 평가 (2026-04-21 저녁) — v4 fuzzer
- `eval_10k_v4_l1l3.json` — A v4 결과 (로컬 14MB, repo에는 요약만)
- `eval_10k_v4_l0_l1l3.json` — C v4 결과
- `eval_10k_v4_l1l4_full.json` — B v4 결과
- `eval_10k_v4_l0_l1l4_full.json` — D v4 결과

## 집계 결과 (모두 repo `PII/results/summaries/` 보존)
- `run_e_final_summary.json` — 1차 4-way 최종
- `run_a_v3_summary.json` — Baseline 초기 분석
- `run_b_10k_summary.json` — L1~L3 baseline 집계
- `run_c_l0_summary.json` — L0 vs Baseline 비교
- `run_d_4way_summary.json` — Cascade 기반 3-way
- `analyze_l0_deep.json` — L0 솔로/잔여 우회 deep dive

## Phase별 산출물 (모두 `PII/results/phase{1,2,3}/` 보존)
- Phase 1: `latency_precise.json`, `mcnemar.json`, `fp_test.json`
- Phase 2: `v4_baseline.json`, `v4_compare.json`, `v4_final_4way.json`
- Phase 3: `ablation.json`, `l4_smart_skip.json`

---

# 🔬 시도했지만 다른 방향으로 간 것들 (실패 학습 기록)

## 시행착오 1: 초기 detection rate "89.4%"
- 처음엔 raw `output != text` 기준으로 89.4% detection이라 봄
- 발견: Presidio가 PERSON만 마스킹하고 진짜 PII는 그대로 둔 케이스 다수
- 수정: TRUE/FALSE/BYPASS 3분류 도입 → real bypass 21%로 정정

## 시행착오 2: Bedrock 평가 도중 깨짐
- 4/19에 Docker 죽으면서 Bedrock 응답이 모두 ERROR
- 원인: LiteLLM v4.69+ config 스키마 변경 (`guardrail_info` 안 → `litellm_params` 직접)
- 수정: config.yaml 패치 + sanity check 50건 검증

## 시행착오 3: Layer 0 False Positive 26%
- 초기 detector는 정상 한국어 문서에서 26% FP
- 원인: 짧은 키워드 ("개", "한국") 단독 매칭 → "3개월", "한국은행" 충돌
- 수정: 2자 이하 값은 컨텍스트 필수 규칙 도입 → 2% FP

## 시행착오 4: GitHub push rejected (synthetic AKIA keys)
- raw eval data에 퍼저 생성 합성 AWS 키 (AKIA + 16자) 포함
- GitHub secret scanner가 진짜 시크릿으로 오인 → push 차단
- 수정: 1,133개 AKIA 패턴을 `AKIAXXXXXXXXXXXXXXXX`로 마스킹 후 amend

## 시행착오 5: cascade_evaluator `--all` 모드 summary 버그
- TRUE 케이스의 L4 결과가 BYPASS여도 "still bypass"로 잘못 카운트
- 결과 요약이 잘못 표시되지만 raw 데이터는 정상
- 후속 집계 (run_e_final_4way) 에서 정상 처리

---

# 🚧 향후 과제 (논문 limitations / 후속 연구)

## 단기 (콘테스트 후)
- [ ] **Azure AI Language PII Redaction** 비교 추가 (5번째 baseline)
- [ ] **Output 퍼저 평가** — `output_payloads_v4.json` (3,025건) 활용
- [ ] **Injection 결합 공격** — Lakera의 진짜 역할 측정

## 중기
- [ ] **다국어 확장** — 일본어, 중국어 Layer 0 (히라가나-카타카나, 번체-간체)
- [ ] **Layer 0 사전 자동 확장** — KLUE NER 또는 KoELECTRA fine-tuning으로 키워드 사전 자동 생성
- [ ] **Latency optimization** — Layer 0 정규식을 Aho-Corasick으로 변환

## 장기
- [ ] Layer 0를 Apache 2.0으로 OSS 공개 (PyPI 패키지)
- [ ] LiteLLM 공식 plugin으로 등록
- [ ] HuggingFace Dataset 정식 publish (CC BY-NC 4.0)

---

# 📌 콘테스트 발표용 핵심 (반드시 포함)

1. **문제**: 영어 중심 가드레일 → 한국어 텍스트형 PII 50% 우회 (KR_semantic 49.62%)
2. **해결책**: Layer 0 (한국어 정규화 + 키워드 사전, LLM 없음)
3. **결과**: GPT-4o-mini judge보다 +8.99%p 우월 (KR_semantic), p < 1e-28
4. **비용**: 220배 빠름 + $0 (vs LLM judge $1.35/10k)
5. **Smart Cascade**: L0 + L4 cascade로 detection 97.23% 유지하면서 LLM 호출 94% 절감
6. **Ablation**: Dict가 96% 기여 → 다른 언어로 확장 가능한 인사이트
7. **Robustness**: validity-first 퍼저 v4에서 우위 더 커짐 (+3.36→+4.56%p)
8. **재현성**: `make all` 단일 명령 + 89 unit tests + GitHub Actions CI

---

> **마지막 업데이트**: 2026-04-23
> **작성자**: 민우 + Claude Opus 4.7 (1M context)
> **다음 업데이트 예정**: 콘테스트 발표 후 (피드백 반영 + 후속 실험 결과)

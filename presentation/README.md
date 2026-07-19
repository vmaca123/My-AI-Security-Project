# presentation/ — 발표 슬라이드 빌더

캡스톤 발표·논문 준비 과정에서 만든 **재현 가능한 슬라이드 생성 스크립트** 모음입니다. 각 스크립트는 [python-pptx](https://python-pptx.readthedocs.io/)로 16:9 슬라이드 1장을 생성합니다.

## 실행 방법

```bash
pip install python-pptx           # 의존성
python presentation/build_engine_arch.py
```

- 폰트는 **맑은 고딕(Malgun Gothic, Windows 기본)** 을 사용합니다.
- 각 스크립트 맨 아래 `out = r"C:\litellm\....pptx"` 줄이 **출력 경로**입니다. 환경에 맞게 바꿔서 실행하세요. (원작성 환경 경로가 하드코딩돼 있음)
- PNG 미리보기는 Windows에서 PowerPoint COM으로 export 가능:
  ```powershell
  $ppt = New-Object -ComObject PowerPoint.Application
  $pres = $ppt.Presentations.Open("<파일>.pptx", $true, $false, $false)
  $pres.Slides.Item(1).Export("<파일>.png", "PNG", 1600, 900)
  $pres.Close(); $ppt.Quit()
  ```

## 슬라이드 목록

| 스크립트 | 생성 슬라이드 | 용도 |
|---|---|---|
| `build_onepage_arch.py` | 전체 아키텍처 1장 (문제→해결, 비전문가용) | 개요 발표 |
| `build_arch_centered.py` | 프로그램 아키텍처 — M1~M9 파이프라인 (가운데 정렬) | 시스템 구조 |
| `build_engine_arch.py` | v0.2 엔진 내부 구조 (M1~M9 + 설계원칙·위험등급 사이드바) | 방법론 상세 |
| `build_m4_context_slide.py` | M4 문맥가중(Context Scoring) — 부스트/페널티/조합 + 예시 | 방법론 심화 |
| `build_baseline_twotable.py` | 베이스라인 두 평가본 교차 비교표 (run_b 79.01% / phase2_v4 80.15%) | 결과·데이터 정합성 |
| `build_research_bg.py` | 연구 배경 (법+증거 결합형: PIPA §23 → 실측 우회) | 서론/동기 |
| `build_research_bg_v2.py` | 연구 배경 v2 (배경답게: 법 → 텍스트형 → 기존 한계 → RQ) | 서론/동기 |

## 데이터 출처

슬라이드 수치는 `PII/results/`(평가 집계)와 `PII/results/data/`(raw eval)에서 나옵니다. 베이스라인 두 평가본(run_b 79.01% vs phase2_v4 80.15%)의 차이는 동일 raw(`eval_10k_l1l3.json`)의 집계 시점·기준 차이이며, 발표 표는 한 기준으로 통일해 사용하세요.

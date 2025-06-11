# MS Project1 

## 금융상품 추천 시스템.

# 💰 소비 데이터 기반 금융상품 추천 시스템

본 프로젝트는 **소비자 소비 데이터를 분석하여 개인 맞춤형 금융상품을 추천하는 AI 기반 시스템**을 구축합니다.  
**Databricks, PySpark, MLflow, Git** 기반으로 대규모 데이터 처리와 협업을 구조화하며, 보안과 실험 재현성을 중시합니다.

---
## Databricks에서 raw-data 접근 경로(가상경로)
  * /mnt/raw-data/[폴더명]/[파일이름].csv

## 📁 프로젝트 디렉토리 설명 및 보안 가이드


### Git의 전체 개요
#### 📁 financial-product-recommender/

├── 📄 README.md                  # 프로젝트 개요 및 실행 방법 안내  
├── 📄 .gitignore                 # Git 추적에서 제외할 파일 및 폴더 목록  
├── 📄 requirements.txt           # 로컬 환경을 위한 Python 패키지 목록  

├── 📁 data/                      # 데이터 디렉토리  
│   ├── 📁 raw/                   # 원본 데이터 (Git에 포함되지 않음)  
│   └── 📁 processed/             # 전처리된 데이터 파일  

├── 📁 notebooks/                 # Databricks 노트북 스크립트  
│   ├── 01_data_preprocessing.py     # 데이터 전처리  
│   ├── 02_feature_engineering.py    # 특성 엔지니어링  
│   ├── 03_model_training.py         # 모델 학습  
│   └── 04_model_evaluation.py       # 모델 평가  

├── 📁 src/                       # 핵심 모듈 (파이썬 스크립트)  
│   ├── data_loader.py             # 데이터 불러오기 및 준비 함수  
│   ├── recommender.py             # 추천 알고리즘 로직  
│   └── utils.py                   # 공통 유틸리티 함수  

├── 📁 experiments/               # 실험 결과 및 설정 저장  
│   ├── v1_basic_model/            # 기본 추천 모델 실험  
│   └── v2_improved_model/         # 개선된 모델 실험  

└── 📁 reports/                   # 분석 보고서 및 시각화  
    └── 📁 figures/                # 그래프 및 이미지 리소스


---

### 📦 1. `data/` — **데이터 디렉토리**

- `raw/`:  
  - 원본 데이터 저장.  
  - 민감 정보(PII, 금융거래내역 포함)가 있을 수 있으므로 **절대 Git에 커밋 금지**.  
  - `*.csv`, `*.json`, `*.parquet` 파일은 `.gitignore`에 반드시 포함.

- `processed/`:  
  - 전처리 후 데이터 저장. 분석에 활용할 수 있지만 여전히 개인정보 위험 존재.

#### 🔒 데이터 보안 가이드

> 참고: [Databricks Data Governance Guide](https://docs.databricks.com/data-governance/index.html), [Google Cloud Data Privacy](https://cloud.google.com/security/privacy)

- 모든 데이터에는 다음 규칙 적용:
  - ✅ 민감 필드(`name`, `email`, `SSN`, `card_number`)는 **해시 또는 익명화 처리**  
  - ✅ API 키 또는 인증 토큰은 코드에 하드코딩하지 말고 `.env` 또는 Key Vault 사용
  - ✅ `data/` 내 모든 데이터는 S3, Azure Blob 등 **권한 기반 저장소**로 이전 권장

---

### 📓 2. `notebooks/` — **분석 및 개발 노트북 (Databricks 기반)**

- 각 단계별 작업 흐름을 Python 스크립트 형태로 정리:
  - `01_data_preprocessing.py`: 결측치 처리, 이상치 탐지, 로그 변환 등
  - `02_feature_engineering.py`: 범주형 인코딩, 사용자 세그멘트 생성
  - `03_model_training.py`: 추천 모델 학습 (예: 유사도 기반, matrix factorization 등)
  - `04_model_evaluation.py`: 성능 평가 및 confusion matrix, ROC 시각화 등

#### 💡 실무 팁

- 실험 재현을 위해 **MLflow로 실험 로그 자동 기록**
- 모델 코드에는 `random_seed`, `train/test split` 고정 포함 필수

---

### 🧠 3. `src/` — **핵심 모듈 코드**

- `data_loader.py`: 데이터 로딩 함수 (S3, Blob, Delta Lake 등에서 불러오기)
- `recommender.py`: 추천 알고리즘 정의 (콘텐츠 기반, 협업 필터링 등)
- `utils.py`: 공통 함수, 로깅, 시드 고정 등 유틸리티

#### 📌 모듈화 이유

- 모델 개선, 실험 재현, 협업 유지보수를 위해 **모듈화 구조 필수**
- 추천 알고리즘은 알고리즘 유형별로 **전략 패턴 또는 클래스화** 권장

---

### 🧪 4. `experiments/` — **모델 실험 결과 및 버전 관리**

- `v1_basic_model/`: 첫 번째 실험 결과 저장소
- `v2_improved_model/`: 하이퍼파라미터 튜닝 및 개선된 알고리즘 기록

#### 🧭 실험 관리 팁

> 참고: [MLflow Tracking Guide](https://mlflow.org/docs/latest/tracking.html)

- 각 실험 디렉토리에는 다음 포함:
  - 학습 파라미터 (`params.json`)
  - 성능 지표 (`metrics.json`)
  - 모델 파일 (`model.pkl` or `MLflow URI`)
  - 에러 로그 (`train.log`)

---

### 📊 5. `reports/` — **보고서 및 시각화 자료**

- 발표용 자료 및 중간 보고서 저장
- `figures/`: matplotlib, seaborn, plotly 등 시각화 결과 저장

#### ✅ 실무용 보고서 팁

- 중간 결과는 `.ipynb`를 HTML 또는 PDF로 변환해 `reports/`에 저장
- 발표자료는 **버전 관리** 및 발표자별 변경 이력 명시

---

### 💡 Git commit 컨벤션 설정법
- [링크참조](https://velog.io/@shin6403/Git-git-%EC%BB%A4%EB%B0%8B-%EC%BB%A8%EB%B2%A4%EC%85%98-%EC%84%A4%EC%A0%95%ED%95%98%EA%B8%B0)
하여 commit 메시지 작성

## 🔐 Git 보안 구성 (`.gitignore`)

> 실제 사고 사례: AWS 키 유출로 인해 수천 달러 손해 ([Source: GitGuardian](https://www.gitguardian.com/blog/top-10-secrets-leaked-on-github-in-2022))

> [How_to_set_gitignore](https://sanghee01.tistory.com/107)

#### `.gitignore`에는 다음 항목 반드시 포함:
1. DATA
    /data/raw/
    /data/processed/
    /reports/.html
    /reports/.pdf

2. 환경설정
    .env
    pycache/

3. DataBricks METADATA
    .dbx

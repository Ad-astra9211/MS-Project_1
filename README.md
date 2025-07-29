# 📊 카드 소비 기반 펀드 추천 시스템

> 본 프로젝트는 AI Hub의 [금융 합성 데이터](https://aihub.or.kr/)를 기반으로 분석 및 재가공한 결과입니다. 해당 데이터는 비상업적 목적으로만 활용되었습니다.

https://pr1sm.cloud/
---


##  프로젝트 개요

- **프로젝트명**: 카드 소비 데이터 분석을 통한 고객 맞춤형 펀드 추천 시스템 개발  
- **프로젝트 기간**: 2025.05.26 ~ 2025.06.10  
- **기술 스택**:  
  `Azure Databricks (Spark)`, `PySpark`, `Flask`, `SQL`, `Pandas`, `Chart.js`, `HTML/CSS`

---

##  팀 구성 및 역할

<img src="https://github.com/Ad-astra9211/MS-Project_1/blob/main/readme_gif/1%20%EB%A1%9C%EA%B3%A0.gif">

| 이름 | 담당 역할 |
|------|-----------|
| [mok010](https://github.com/mok010) |  Data Scientist |
| [Ad-astra9211](https://github.com/Ad-astra9211) |  Data Engineer |
| [Happybin72](https://github.com/Happybin72) | Project Leader |
| [vitaje](https://github.com/vitaje) |  Project Manager |
| [saltedsugar1117](https://github.com/saltedsugar1117) | Data Scientist |
| [손아현] | Service Architecture |

---

##  프로젝트 목표 및 특징

- 카드 소비 데이터를 기반으로 고객을 클러스터링하여 유사 고객 그룹별로 맞춤형 펀드 추천
- 약 14GB 규모의 금융 데이터를 Spark 기반으로 대용량 처리
- 머신러닝으로 투자위험등급 예측 모델링 수행
- Flask 기반 웹 서비스로 분석 결과 실시간 제공
- 내부(Chart.js) 및 외부(Databricks) 대시보드를 함께 제공

---

##  고객 클러스터링 기반 맞춤 추천

<img src="https://github.com/Ad-astra9211/MS-Project_1/blob/main/readme_gif/2%20%EC%83%98%ED%94%8C%EC%BD%94%EB%93%9C.gif">
<img src="https://github.com/Ad-astra9211/MS-Project_1/blob/main/readme_gif/3%20%EC%B6%94%EC%B2%9C%20%EC%84%B8%EB%B6%80.gif">
<img src="https://github.com/Ad-astra9211/MS-Project_1/blob/main/readme_gif/%ED%81%B4%EB%9F%AC%EC%8A%A4%ED%84%B0%EB%A7%81.png">

- 카드 소비 및 금융 행동 데이터를 바탕으로 KMeans 등의 클러스터링 기법을 사용
- `member_code`를 입력받아 해당 고객의 클러스터 정보 확인
- 각 클러스터에 대한 조건을 딕셔너리 형태로 관리하고 SQL 필터에 동적으로 반영

###  사용자별 필터링 로직 예시

```python
cluster_fund_filter_conditions = {
    0: {"펀드성과정보_1년": "> 0.05", "성장주": "> 0.5"},
    1: {"글로벌": "> 0.3", "투자위험등급": "<= 3"},
    2: {"가치주": "> 0.4", "펀드표준편차_1년": "< 0.2"}
}
```

- 추천 결과 페이지에서는 적용된 필터를 뱃지 형태로 시각화하여 제공

---

##  데이터 전처리 및 스케일링

- 결측치 처리: 주요 지표 결측 시 제거, 보완 가능한 값은 중앙값 등으로 대체
- 이상치 처리: IQR 기준 제거, Yeo-Johnson 및 log 변환 적용
- 스케일링: MinMaxScaler로 수익률, 유입금액, 수수료 등 정규화
- 펀드 추천 점수 산정:

```python
추천점수 = 0.5 * 수익률점수 + 0.3 * 자금유입점수 + 0.2 * 수수료점수
```

---

##  머신러닝 기반 투자위험등급 예측

- `투자위험등급` 결측값 보완을 위한 모델링
- 사용 모델:
  - ✅ SparkXGBClassifier (최종 선택, Accuracy 0.97)
  - RandomForestClassifier
  - LogisticRegression
- 중요 피처: `펀드표준편차_1년`, `MaximumDrawDown_1년`, `추천랭킹`

---

##  웹 서비스 구조 (Flask 기반)

### 주요 라우트

| 경로 | 설명 |
|------|------|
| `/` | 회원코드 입력 페이지 |
| `/recommend` | 클러스터 기반 펀드 추천 결과 |
| `/fund/<code>` | 펀드 상세 페이지 |
| `/dashboard` | Chart.js 기반 내부 대시보드 |
| `/db_dash` | Databricks 대시보드 임베딩

---

##  이중 대시보드 시스템

### 1️. 내부 대시보드 `/dashboard`

<img src="https://github.com/Ad-astra9211/MS-Project_1/blob/main/readme_gif/4%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C1.gif">

- Chart.js 기반 시각화
- 주요 지표:
  - 월별 신규 펀드 설정 수
  - 수익률 합계
  - 테마별 펀드 점유율
  - 사용자 펀드 이용 통계 등

### 2️. 외부 대시보드 `/db_dash`

<img src="https://github.com/Ad-astra9211/MS-Project_1/blob/main/readme_gif/5%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C2.gif">

- Databricks에서 만든 BI 대시보드 iframe 임베딩
- Azure 인증 필요
- 운영 환경에서도 즉시 반영 가능

```python
@app.route('/db_dash')
def databricks_dashboard():
    dashboard_url = os.getenv("DATABRICKS_DASHBOARD_URL")
    return render_template('db_dash.html', dashboard_url=dashboard_url)
```

---

##  더 자세한 구현 설명
https://star-ccomputer-go.tistory.com/category/Data/%EC%B9%B4%EB%93%9C%EC%86%8C%EB%B9%84%EB%8D%B0%EC%9D%B4%ED%84%B0%20%EB%B6%84%EC%84%9D%20%EA%B3%A0%EA%B0%9D%20%EB%A7%9E%EC%B6%A4%ED%98%95%20%ED%8E%80%EB%93%9C%EC%B6%94%EC%B2%9C%EC%8B%9C%EC%8A%A4%ED%85%9C

환경에 맞게 수정만 하면 작동. 
/src/containerized 안에 push, docker-readme.md, k8s-readme.md에 간단하게 가이드라인 有

© 2025 PR1SM Analytics  
이 프로젝트는 비상업적 교육 목적으로 진행되었습니다.

# Docker 환경 설정 가이드

## 🚀 Docker 배포 시작하기

### 1단계: Docker 설치

**Windows/Mac 사용자:**
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) 다운로드 후 설치
2. 설치 완료 후 Docker Desktop 실행
3. 터미널에서 `docker --version` 명령어로 설치 확인

**Linux 사용자:**
Linux에서의 Docker 설치는 배포판마다 다르므로, 공식 Docker 설치 가이드를 따라주세요:
- **공식 설치 가이드**: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)
- Ubuntu, Debian, Fedora, CentOS, RHEL 등 주요 배포판별 상세 가이드가 제공됩니다.

> **참고**: 설치 후 `sudo usermod -aG docker $USER` 명령으로 현재 사용자를 docker 그룹에 추가하고, 터미널을 재시작하면 `sudo` 없이 docker 명령을 사용할 수 있습니다.

### 2단계: 프로젝트 클론하기
```bash
# 프로젝트 클론
git clone https://github.com/Ad-astra9211/MS-Project_1
cd MS_Project_1

# 프로젝트 구조 확인
ls -la
```

### 3단계: 환경 변수 파일 생성
프로젝트에 포함된 `env.example` 파일을 복사해서 `.env` 파일을 만들어주세요.

```bash
# env.example을 복사해서 .env 파일 생성
cp env.example .env

# 텍스트 에디터로 .env 파일 편집
nano .env
# 또는
code .env
```

`.env` 파일에서 다음 값들을 실제 값으로 변경해주세요:
- `POSTGRES_PASSWORD`: 강력한 비밀번호로 변경
- `MB_EMBEDDING_SECRET_KEY`: 32자 이상의 랜덤 문자열로 변경

⚠️ **중요**: 실제 운영환경에서는 반드시 강력한 비밀번호를 사용

### 4단계: 데이터베이스 파일 준비
`docker-compose up` 명령을 실행하기 전, `local_app.db` 파일을 프로젝트의 최상위 폴더(`docker-compose.yaml` 파일이 있는 곳)에 위치시켜야 합니다.

### 5단계: 첫 실행하기
이 프로젝트는 두 가지 실행 방법을 제공합니다.
- **프로덕션 (추천)**: 코드를 수정하지 않고 사전 빌드된 이미지를 사용하여 빠르게 실행합니다.
- **개발**: 코드를 수정한 후 직접 이미지를 빌드하여 실행합니다.

#### 프로덕션 환경에서 실행 (사전 빌드된 이미지 사용)
대부분의 사용자는 이 방식을 사용하는 것을 추천합니다. 이미지를 빌드하지 않고 바로 실행하므로 더 빠르고 간편합니다.

```bash
# -f 옵션으로 docker-compose.prod.yaml 파일을 지정하여 실행
docker-compose -f docker-compose.prod.yaml up -d
```

#### 개발 환경에서 실행 (직접 이미지 빌드)
소스 코드를 직접 수정했거나, 최신 변경사항을 반영하여 이미지를 빌드하고 싶을 때 사용합니다.

```bash
# 기본 docker-compose.yaml 파일을 사용하여 실행 (이미지 빌드 과정 포함)
docker-compose up -d
```

### 6단계: 접속 확인
브라우저에서 다음 주소들을 확인해보세요:
- **Flask 앱**: http://localhost:5000
- **Metabase**: http://localhost:3000

## 사전 요구사항

- Docker & Docker Compose
- Git
- `.env` 파일 (환경 변수 설정)

## 환경 변수 설정

프로젝트에 포함된 `env.example` 파일을 참고하여 `.env` 파일을 생성해주세요:

```bash
cp env.example .env
```

`env.example` 파일 내용:
```env
# PostgreSQL 데이터베이스 설정
POSTGRES_USER=metabase_user
POSTGRES_PASSWORD=your_secure_password_here

# Metabase 설정
MB_EMBEDDING_SECRET_KEY=your_32_character_secret_key_here
```

각 변수 설명:
- `POSTGRES_USER`: PostgreSQL 사용자명
- `POSTGRES_PASSWORD`: PostgreSQL 비밀번호 (보안을 위해 변경 필요)
- `MB_EMBEDDING_SECRET_KEY`: Metabase 임베딩 시크릿 키 (32자 이상 랜덤 문자열)

## 서비스 구성

### 1. PostgreSQL (metabase_postgres)
- **이미지**: postgres:15-alpine
- **포트**: 5432
- **용도**: Metabase 메타데이터 저장소
- **데이터 볼륨**: `./postgres_data:/var/lib/postgresql/data`

### 2. Metabase (metabase)
- **포트**: 3000
- **빌드**: Dockerfile.metabase
- **접속 URL**: https://dashboard.pr1sm.cloud
- **플러그인**: `./metabase-plugins` 디렉토리의 플러그인들
- **데이터베이스**: `./local_app.db` (읽기 전용)

### 3. Flask 애플리케이션 (pr1sm_flask)
- **포트**: 5000 (호스트) → 5000 (컨테이너)
- **빌드**: Dockerfile.pr1sm_flask
- **소스 코드**: `./src` 디렉토리
- **데이터베이스**: `./local_app.db` (읽기 전용)

## 실행 방법

이해를 돕기 위해, 위 5단계에서 설명한 두 가지 실행 방법을 다시 한번 정리합니다.

### 전체 스택 시작

#### 프로덕션 (추천)
```bash
docker-compose -f docker-compose.prod.yaml up -d
```

#### 개발
```bash
docker-compose up -d
```

### 특정 서비스만 시작

#### 프로덕션 환경
```bash
# PostgreSQL만 시작
docker-compose -f docker-compose.prod.yaml up -d postgres

# Metabase만 시작 (PostgreSQL 의존성 자동 시작)
docker-compose -f docker-compose.prod.yaml up -d metabase

# Flask 앱만 시작
docker-compose -f docker-compose.prod.yaml up -d pr1sm_flask
```

#### 개발 환경
```bash
# PostgreSQL만 시작
docker-compose up -d postgres

# Metabase만 시작 (PostgreSQL 의존성 자동 시작)
docker-compose up -d metabase

# Flask 앱만 시작
docker-compose up -d pr1sm_flask
```

### 로그 확인

#### 프로덕션 환경
```bash
# 전체 로그
docker-compose -f docker-compose.prod.yaml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.prod.yaml logs -f metabase
docker-compose -f docker-compose.prod.yaml logs -f pr1sm_flask
docker-compose -f docker-compose.prod.yaml logs -f postgres
```

#### 개발 환경
```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f metabase
docker-compose logs -f pr1sm_flask
docker-compose logs -f postgres
```

### 서비스 중지

#### 프로덕션 환경
```bash
# 전체 중지
docker-compose -f docker-compose.prod.yaml down

# 볼륨까지 삭제
docker-compose -f docker-compose.prod.yaml down -v
```

#### 개발 환경
```bash
# 전체 중지
docker-compose down

# 볼륨까지 삭제
docker-compose down -v
```

## 접속 정보

- **Metabase**: http://localhost:3000
- **Flask 애플리케이션**: http://localhost:5000 (프로덕션 환경에서는 http://localhost:5100)
- **PostgreSQL**: localhost:5432

## 주의사항

1. **읽기 전용 DB**: `local_app.db`는 읽기 전용으로 마운트됩니다.
2. **헬스체크**: PostgreSQL 서비스가 완전히 시작된 후 Metabase가 시작됩니다.
3. **포트 차이**: 프로덕션 환경에서는 Flask 앱이 5100 포트를 사용합니다.

## 트러블슈팅

### 포트 충돌 시
기본 포트가 사용 중인 경우 `docker-compose.yaml` 또는 `docker-compose.prod.yaml`에서 포트를 변경하세요:
```yaml
ports:
  - "다른포트:3000"  # Metabase
  - "다른포트:5000"  # Flask (개발)
  - "다른포트:5100"  # Flask (프로덕션)
  - "다른포트:5432"  # PostgreSQL
```

### Docker 권한 문제 (Linux)
Linux에서 "permission denied" 오류가 발생하는 경우:
```bash
# 현재 사용자가 docker 그룹에 속해 있는지 확인
groups $USER

# docker 그룹이 없다면 다시 추가
sudo usermod -aG docker $USER

# 터미널 재시작 또는 재로그인 후 다시 시도
```

### 컨테이너 상태 확인
```bash
# 실행 중인 컨테이너 확인
docker ps

# 모든 컨테이너 확인 (중지된 것 포함)
docker ps -a

# 특정 컨테이너 로그 확인
docker logs <컨테이너_이름>
```
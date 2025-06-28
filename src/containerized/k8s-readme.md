# Kubernetes 배포 가이드

이 문서는 애플리케이션을 Kubernetes 클러스터에 배포하는 방법을 안내합니다.

## 🚀 배포 절차 요약

1.  **사전 준비**: `kubectl`, `podman`(선택) 등 필요한 도구를 설치하고 클러스터에 연결합니다.
2.  **Secrets 설정**: `k8s/secrets.yaml` 파일에 민감한 정보를 입력합니다.
3.  **컨테이너 이미지 준비**: 제공된 이미지를 사용하거나, 필요 시 직접 빌드하여 레지스트리에 푸시합니다.
4.  **DB 초기화 Job 실행**: Google Drive에서 대용량 `local_app.db` 파일을 다운로드하는 Job을 실행합니다.
5.  **애플리케이션 배포**: PostgreSQL, Metabase, Flask 앱을 배포합니다.
6.  **Metabase 대시보드 ID 업데이트**: 배포 후 생성된 Metabase 대시보드 ID를 `secrets.yaml`에 반영합니다.

---

## 1. 사전 준비

### 1-1. Kubernetes 클러스터 준비

먼저 Kubernetes 클러스터가 필요합니다. 사용 목적과 환경에 따라 다음 옵션 중 하나를 선택하세요:

#### **로컬 개발/테스트 환경 (추천)**

**Minikube** - 가장 쉬운 시작 방법
- **특징**: 단일 노드 Kubernetes 클러스터를 로컬 VM에서 실행
- **장점**: 설치가 간단하고, Docker Desktop과 통합 가능
- **적합한 경우**: Kubernetes를 처음 배우거나 개발/테스트 목적
- **설치 가이드**: [https://minikube.sigs.k8s.io/docs/start/](https://minikube.sigs.k8s.io/docs/start/)

**k3s** - 경량화된 Kubernetes
- **특징**: 메모리 사용량이 적고 빠른 설치가 가능한 경량 Kubernetes
- **장점**: 리소스 사용량이 적고, IoT나 엣지 환경에 적합
- **적합한 경우**: 제한된 리소스 환경이나 빠른 프로토타이핑
- **설치 가이드**: [https://k3s.io/](https://k3s.io/)

#### **프로덕션 환경**

**kubeadm** - 표준 설치 도구
- **특징**: 공식 Kubernetes 설치 도구로 클러스터를 직접 구성
- **장점**: 완전한 제어권과 커스터마이징 가능
- **적합한 경우**: 온프레미스 환경에서 프로덕션 클러스터 구축
- **설치 가이드**: [https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/)

**클라우드 관리형 서비스** - 운영 부담 최소화
- **Azure Kubernetes Service (AKS)**: [https://azure.microsoft.com/ko-kr/products/kubernetes-service](https://azure.microsoft.com/ko-kr/products/kubernetes-service)
- **Amazon Elastic Kubernetes Service (EKS)**: [https://aws.amazon.com/ko/eks/](https://aws.amazon.com/ko/eks/)
- **Google Kubernetes Engine (GKE)**: [https://cloud.google.com/kubernetes-engine](https://cloud.google.com/kubernetes-engine)
- **장점**: 마스터 노드 관리가 자동화되고, 확장성과 안정성이 뛰어남
- **적합한 경우**: 프로덕션 환경에서 운영 부담을 줄이고 싶은 경우

> 처음 시작하신다면 **Minikube**를 사용하세요. 설치가 가장 간단하고 이 가이드의 모든 기능을 테스트할 수 있습니다.

### 1-2. 필수 도구 설치
- **kubectl**: Kubernetes 클러스터와 통신하기 위한 필수 CLI 도구입니다. [설치 가이드](https://kubernetes.io/docs/tasks/tools/)
- **(선택) podman 또는 docker**: 컨테이너 이미지를 직접 빌드할 경우 필요합니다.

### 1-3. Kubernetes 클러스터 연결 확인
```bash
# 클러스터 정보 확인 (에러가 없어야 함)
kubectl cluster-info

# 노드 상태 확인 (Ready 상태여야 함)
kubectl get nodes
```

---

## 2. Secrets 설정

배포에 필요한 민감한 정보들을 `k8s/secrets.yaml` 파일에 설정합니다. 템플릿 파일을 복사하여 사용하세요.

```bash
# k8s 디렉토리로 이동
cd k8s

# secrets.yaml.template을 secrets.yaml로 복사
cp secrets.yaml.template secrets.yaml

# 텍스트 에디터로 secrets.yaml 파일 편집
nano secrets.yaml
```

**⚠️ 중요: `secrets.yaml` 파일의 다음 값들을 실제 값으로 반드시 변경해야 합니다.**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pr1sm-secrets
# ... (설명)
stringData:
  postgres-password: "YOUR_STRONG_POSTGRES_PASSWORD" # ◀ PostgreSQL 비밀번호
  metabase-secret-key: "YOUR_32_CHAR_METABASE_SECRET_KEY" # ◀ Metabase 시크릿 키 (32자 이상)
---
apiVersion: v1
kind: Secret
metadata:
  name: flask-app-secrets
# ... (설명)
stringData:
  METABASE_SITE: "https://your-metabase-domain.com" # ◀ Metabase 접속 주소
  METABASE_SECRET: "YOUR_32_CHAR_METABASE_SECRET_KEY" # ◀ 위와 동일한 Metabase 시크릿 키
  GOOGLE_DRIVE_FILE_ID: "YOUR_GOOGLE_DRIVE_FILE_ID" # ◀ local_app.db의 파일 ID
  
  # [!!] 아래 2개 값은 배포 후 마지막 단계에서 수정합니다.
  METABASE_DASH_ID: "1" # ◀ 임시로 "1"을 입력
  METABASE_DASH_URL: "http://temp" # ◀ 임시로 "http://temp"를 입력
```
> **Git 주의**: `secrets.yaml` 파일은 민감 정보를 포함하므로 절대 Git에 커밋해서는 안 됩니다. `.gitignore`에 `k8s/secrets.yaml`이 포함되어 있는지 확인하세요.

---

## 3. 컨테이너 이미지 준비 (선택사항)

기본적으로 `k8s/app.yaml` 에는 `quay.io/vitaje/pr1sm-metabase:latest` 와 `quay.io/vitaje/pr1sm-flask:latest` 로 이미지가 설정되어 있어 별도의 빌드 과정 없이 배포할 수 있습니다.

만약 코드를 수정하여 직접 이미지를 빌드하고 싶다면, 다음 절차를 따르세요.

### 3-1. 빌드 스크립트 수정
프로젝트 루트의 `build-and-push-quay.sh` 파일을 열어 `QUAY_USERNAME`과 `VERSION`을 자신의 환경에 맞게 수정합니다.

```sh
# build-and-push-quay.sh
QUAY_USERNAME="your-quay-username"  # ◀ 본인의 Quay.io 사용자명으로 변경
VERSION="1.0.0"                   # ◀ 원하는 버전 태그로 변경
```

### 3-2. 빌드 및 푸시 실행
스크립트를 실행하여 이미지를 빌드하고 Quay.io 레지스트리에 푸시합니다.

```bash
# 스크립트 실행 권한 부여
chmod +x build-and-push-quay.sh

# 스크립트 실행
./build-and-push-quay.sh
```

### 3-3. `app.yaml` 이미지 주소 변경
빌드가 완료되면 `k8s/app.yaml` 파일의 이미지 주소를 방금 푸시한 당신의 이미지 주소로 변경해야 합니다.

```yaml
# k8s/app.yaml

# ...
      - name: pr1sm-flask
        image: quay.io/your-quay-username/pr1sm-flask:latest # ◀ 변경
# ...
# ...
      - name: metabase
        image: quay.io/your-quay-username/pr1sm-metabase:latest # ◀ 변경
# ...
```

---

## 4. 데이터베이스 초기화 Job 실행

이 단계에서는 `local_app.db` (약 2.4GB) 파일을 Google Drive에서 다운로드하여 Persistent Volume에 저장하는 Job을 실행합니다.

```bash
# Secrets 먼저 적용
kubectl apply -f k8s/secrets.yaml

# 데이터베이스 초기화 Job 실행
kubectl apply -f k8s/job.yaml
```

**Job 상태 확인:**
```bash
# Job이 완료될 때까지 상태 확인 (STATUS가 'Completed'가 되어야 함)
kubectl get jobs -w

# 다운로드 로그 확인
kubectl logs job/db-initializer-job -f
```
> `job.yaml`은 `gdown` 도구가 설치된 `wernight/gdown` 이미지를 사용하여 안정적으로 파일을 다운로드합니다.

---

## 5. 애플리케이션 배포

핵심 애플리케이션(PostgreSQL, Metabase, Flask)들을 배포합니다.

```bash
# app.yaml 파일로 모든 리소스 배포
kubectl apply -f k8s/app.yaml

# 배포 상태 확인
kubectl get pods -w
```
모든 Pod들이 `Running` 상태가 되면 다음 단계를 진행합니다.

---

## 6. Metabase 대시보드 ID 업데이트

애플리케이션이 모두 배포되었지만, Flask 앱이 올바른 Metabase 대시보드를 임베딩하려면 실제 대시보드 ID와 URL이 필요합니다.

### 6-1. Metabase 접속 및 대시보드 생성
- `kubectl get services` 명령으로 `metabase-service`의 외부 IP(EXTERNAL-IP)를 확인하여 접속합니다.
- Metabase 초기 설정을 완료하고, `local_app.db`를 데이터 소스로 추가합니다.
- 분석에 사용할 대시보드를 생성하고 **공개 공유(Public sharing)** 설정을 활성화합니다.

### 6-2. 대시보드 정보 확인
- 생성된 대시보드의 URL을 확인합니다. URL에서 **대시보드 ID(숫자)**와 **전체 공개 URL**을 복사합니다.
  - 예: `http://<METABASE-IP>/public/dashboard/a1b2c3d4-e5f6...`
  - 이 때 `a1b2c3d4-e5f6...` 부분이 **공개 URL**이며, 대시보드 설정 페이지에서 **ID(숫자)**를 찾을 수 있습니다.

### 6-3. Secrets 업데이트 및 재배포
`k8s/secrets.yaml` 파일을 다시 열고, 임시로 입력했던 값을 실제 값으로 변경합니다.

```yaml
# k8s/secrets.yaml
stringData:
  # ...
  METABASE_DASH_ID: "YOUR_REAL_DASHBOARD_ID"       # ◀ 실제 대시보드 ID (예: "5")
  METABASE_DASH_URL: "YOUR_REAL_PUBLIC_DASH_URL"  # ◀ 실제 공개 URL
```

변경된 `secrets.yaml`을 적용하고, 변경된 설정을 읽어오도록 Flask 앱을 재시작합니다.

```bash
# 변경된 Secret 적용
kubectl apply -f k8s/secrets.yaml

# Flask 앱 재시작
kubectl rollout restart deployment/pr1sm-flask
```

이제 모든 배포 과정이 완료되었습니다. Flask 서비스의 외부 IP로 접속하여 대시보드가 정상적으로 보이는지 확인하세요.

---
## 🔧 기타 운영 가이드

### PostgreSQL 데이터 마이그레이션

로컬 Docker Compose 환경에서 사용하던 PostgreSQL 데이터를 Kubernetes의 영구 볼륨(PVC)으로 이전하는 상세 절차입니다. 이 작업을 통해 로컬에서 사용하던 Metabase의 모든 설정과 데이터를 Kubernetes 환경에서 그대로 사용할 수 있습니다.

#### 사전 준비
-   로컬 환경에 Docker Compose로 실행했던 `postgres_data` 디렉토리가 있어야 합니다.
-   Kubernetes에 PostgreSQL, Metabase 등 `k8s/app.yaml`의 모든 리소스가 배포되어 있어야 합니다.

#### 마이그레이션 절차

##### 1단계: PostgreSQL 서비스 중지
데이터 일관성을 보장하기 위해 PostgreSQL Pod을 0개로 축소하여 안전하게 중지합니다.

```bash
# pr1sm 네임스페이스의 postgres StatefulSet을 0으로 축소
kubectl scale statefulset postgres --replicas=0 -n pr1sm

# Pod이 완전히 종료될 때까지 확인
kubectl get pods -n pr1sm -w | grep postgres
```
> **참고:** 사용자의 네임스페이스가 `pr1sm`이 아닌 경우, 명령어의 `-n pr1sm` 부분을 실제 네임스페이스로 변경해주세요.

##### 2단계: 임시 마이그레이션 Pod 생성
PostgreSQL의 영구 볼륨(PVC)에 접근하여 데이터를 복사할 수 있도록 임시 Pod을 생성합니다.

1.  **`k8s/temp-postgres-migration.yaml` 파일 확인**: 이 파일은 PVC를 마운트하는 `alpine` 이미지 기반의 간단한 Pod을 정의합니다.

2.  **임시 Pod 배포**:
    ```bash
    kubectl apply -f k8s/temp-postgres-migration.yaml
    ```

3.  **Pod 준비 상태 확인**:
    ```bash
    kubectl wait --for=condition=Ready pod/postgres-migration-pod -n pr1sm --timeout=120s
    ```

##### 3단계: 로컬 데이터 복사
로컬의 `postgres_data` 디렉토리 전체를 임시 Pod을 통해 PVC로 복사합니다.

```bash
# kubectl cp <로컬 소스> <Pod 이름>:<Pod 내부 경로> -n <네임스페이스>
kubectl cp postgres_data postgres-migration-pod:/var/lib/postgresql/data/pgdata -n pr1sm
```
> **경고:** 이 작업은 로컬 `postgres_data`의 크기에 따라 몇 분 이상 소요될 수 있습니다.

##### 4단계: 파일 권한 설정
PostgreSQL 컨테이너는 보안을 위해 특정 사용자(ID 70) 권한으로 실행됩니다. 복사된 데이터의 소유자와 권한을 PostgreSQL이 인식할 수 있도록 변경해야 합니다.

```bash
kubectl exec -it postgres-migration-pod -n pr1sm -- sh -c "
echo '=> 복사된 데이터 확인...'
ls -la /var/lib/postgresql/data/

echo '=> PostgreSQL을 위한 파일 소유자 및 권한 변경 (chown/chmod)...'
chown -R 70:70 /var/lib/postgresql/data/pgdata
chmod -R 700 /var/lib/postgresql/data/pgdata

echo '=> 권한 변경 완료. 최종 상태 확인:'
ls -la /var/lib/postgresql/data/
"
```

##### 5단계: 정리 및 서비스 재시작
마이그레이션이 완료되었으므로 임시 Pod을 삭제하고 PostgreSQL 서비스를 다시 시작합니다.

```bash
# 임시 Pod 삭제
kubectl delete pod postgres-migration-pod -n pr1sm

# PostgreSQL StatefulSet을 다시 1로 스케일업
kubectl scale statefulset postgres --replicas=1 -n pr1sm
```

#### 최종 확인
1.  **PostgreSQL 로그 확인**: Pod이 정상적으로 시작되고 데이터를 인식하는지 확인합니다.
    ```bash
    kubectl logs statefulset/postgres -n pr1sm -f
    ```

2.  **Metabase 재시작 및 확인**: 마이그레이션된 데이터를 Metabase가 올바르게 읽을 수 있도록 재시작합니다.
    ```bash
    kubectl rollout restart deployment/metabase -n pr1sm
    ```
    재시작 후 Metabase에 접속하여 기존 대시보드와 설정이 모두 정상적으로 보이는지 확인합니다.

### 리소스 삭제
```bash
# 모든 리소스 삭제
kubectl delete -f k8s/app.yaml
kubectl delete -f k8s/job.yaml
kubectl delete -f k8s/secrets.yaml
kubectl delete pvc local-db-pvc metabase-plugins-pvc postgres-storage-postgres-0
```
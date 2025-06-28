#!/bin/bash

# 설정 변수들
QUAY_USERNAME=""  # 실제 Quay.io 사용자명으로 변경하세요
VERSION=""  # 원하는 버전으로 변경하세요
REGISTRY="quay.io"

# 색상 출력을 위한 함수
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# 스크립트 실행 전 변수 확인
if [[ -z "$QUAY_USERNAME" || -z "$VERSION" ]]; then
    print_error "스크립트 상단의 QUAY_USERNAME과 VERSION 변수를 설정해야 합니다."
    exit 1
fi

# Podman 설치 및 실행 확인
print_info "Podman이 설치되어 있는지 확인 중..."
if ! command -v podman &> /dev/null; then
    print_error "Podman이 설치되지 않았습니다. Podman을 설치하고 다시 시도하세요."
    exit 1
fi

if ! podman info > /dev/null 2>&1; then
    print_error "Podman이 실행되지 않았습니다. Podman을 시작하고 다시 시도하세요."
    exit 1
fi

# Podman으로 Quay.io에 로그인 확인
print_info "Quay.io 로그인 상태 확인 중..."
if ! podman login --get-login ${REGISTRY} > /dev/null 2>&1; then
    print_info "Quay.io에 로그인이 필요합니다."
    print_info "Quay.io 계정이 없다면 https://quay.io 에서 가입하세요."
    podman login ${REGISTRY}
fi

# Metabase 이미지 빌드 (x86-64)
print_info "Metabase x86-64 이미지 빌드 중..."
podman build \
    --platform linux/amd64 \
    --file Dockerfile.metabase \
    --tag ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-amd64 \
    .

if [ $? -ne 0 ]; then
    print_error "Metabase x86-64 이미지 빌드 실패!"
    exit 1
fi

# Metabase 이미지 빌드 (ARM64)
print_info "Metabase ARM64 이미지 빌드 중..."
podman build \
    --platform linux/arm64 \
    --file Dockerfile.metabase \
    --tag ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-arm64 \
    .

if [ $? -ne 0 ]; then
    print_error "Metabase ARM64 이미지 빌드 실패!"
    exit 1
fi

# Flask 이미지 빌드 (x86-64)
print_info "Flask x86-64 이미지 빌드 중..."
podman build \
    --platform linux/amd64 \
    --file Dockerfile.pr1sm_flask \
    --tag ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-amd64 \
    .

if [ $? -ne 0 ]; then
    print_error "Flask x86-64 이미지 빌드 실패!"
    exit 1
fi

# Flask 이미지 빌드 (ARM64)
print_info "Flask ARM64 이미지 빌드 중..."
podman build \
    --platform linux/arm64 \
    --file Dockerfile.pr1sm_flask \
    --tag ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-arm64 \
    .

if [ $? -ne 0 ]; then
    print_error "Flask ARM64 이미지 빌드 실패!"
    exit 1
fi

# 이미지 푸시 (Metabase)
print_info "Metabase 이미지들을 Quay.io에 푸시 중..."
podman push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-amd64
podman push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-arm64

# 이미지 푸시 (Flask)
print_info "Flask 이미지들을 Quay.io에 푸시 중..."
podman push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-amd64
podman push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-arm64

# 멀티 아키텍처 매니페스트 생성 및 푸시 (Metabase)
print_info "Metabase 멀티 아키텍처 매니페스트 생성 중..."
podman manifest create ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION} ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-amd64
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION} ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-arm64
podman manifest push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}

# latest 태그 생성 (Metabase)
podman manifest create ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:latest
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:latest ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-amd64
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:latest ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-arm64
podman manifest push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:latest

# 멀티 아키텍처 매니페스트 생성 및 푸시 (Flask)
print_info "Flask 멀티 아키텍처 매니페스트 생성 중..."
podman manifest create ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION} ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-amd64
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION} ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-arm64
podman manifest push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}

# latest 태그 생성 (Flask)
podman manifest create ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:latest
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:latest ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-amd64
podman manifest add ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:latest ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-arm64
podman manifest push ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:latest

print_success "모든 이미지가 성공적으로 빌드되고 Quay.io에 푸시되었습니다!"
print_info "멀티 아키텍처 이미지 태그:"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:latest"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:latest"
print_info ""
print_info "개별 아키텍처 이미지 태그:"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-amd64"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:${VERSION}-arm64"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-amd64"
print_info "  - ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:${VERSION}-arm64"
print_info ""
print_info "📌 중요: k8s/app.yaml 파일에서 이미지 주소를 다음과 같이 변경하세요:"
print_info "  - image: ${REGISTRY}/${QUAY_USERNAME}/pr1sm-metabase:latest"
print_info "  - image: ${REGISTRY}/${QUAY_USERNAME}/pr1sm-flask:latest" 
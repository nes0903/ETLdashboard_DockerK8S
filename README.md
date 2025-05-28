# ETLdashboard_DockerK8S
◆ 프로젝트 개요

이 프로젝트는 위해상품 관련 공공 데이터를 자동 수집하여 분석 가능한 형태로 정제하고,
웹 대시보드를 통해 실시간 시각화하는 **데이터 파이프라인 + 관제 시스템**입니다.

- Python 기반 ETL 자동화
- MySQL 이중 DB 구조 (원본 kopo / 분석용 kopo2)
- Express.js + EJS 웹 대시보드
- Docker로 컨테이너화, Kubernetes로 배포
- Ingress + MetalLB로 외부 접근 지원

---

◆ 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| 데이터 수집 및 분석 | Python, Pandas, openpyxl, numpy |
| 웹 서버 | Node.js, Express.js, EJS |
| 데이터베이스 | MySQL 8.x (Docker 기반) |
| 컨테이너화 | Docker, DockerHub |
| 오케스트레이션 | Kubernetes (Deployment, Service, PVC, Ingress) |
| 웹 접근 | MetalLB + Ingress (LoadBalancer 타입) |

---

◆ 주요 기능

### 1. ETL 자동화
- GitHub에서 위해상품 Excel 다운로드
- Pandas로 테이블 생성 및 데이터 삽입
- 다중 테이블 JOIN 및 `위해상품_위험도_분석` 생성
- JSON + 텍스트로 구성된 학습용 `데이터셋` 테이블 생성

### 2. 데이터 검증
- 행 개수, NULL, 중복, 위험도등급 유효성 검증
- 검증 결과는 이력 테이블에 저장 (`데이터셋_최신화_이력`)

### 3. 웹 대시보드
- `/api/etl-status`: ETL 작업 및 검증 이력 조회
- `/api/dangerous-products`: 위해상품 분석 데이터 출력
- Bootstrap 기반 UI, 30초마다 실시간 갱신

---

◆ 시스템 아키텍처

```plaintext
GitHub Excel
   ↓
[ETL Pod]
   ↓
[source-db (kopo)]
   ↓
[target-db (kopo2)] ← 분석 테이블 및 JSON 데이터셋
   ↓
[Web Pod (Express.js)]
   ↓
[Ingress + MetalLB]
   ↓
브라우저 대시보드 접속

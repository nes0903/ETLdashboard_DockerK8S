# Python 3.9 이미지를 기반으로 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일들을 복사
COPY kopo_to_kopo2_etl.py .
COPY data_validation.py .
COPY run_etl.sh .
COPY requirements.txt .

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 실행 권한 부여
RUN chmod +x run_etl.sh

# 도커 허브 계정 정보 설정
LABEL maintainer="nes0903"
LABEL version="1.0"
LABEL description="ETL application for kopo to kopo2 data transfer"

# ETL 스크립트 실행
CMD ["python","./run_etl.sh"] 
import mysql.connector
import logging
from datetime import datetime
import os
import time

# 로그 설정
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 데이터베이스 연결 설정
LOCAL_DB_CONFIG = {
    'host': os.getenv('SOURCE_DB_HOST', '10.110.126.86'),  # source-db-service IP
    'port': int(os.getenv('SOURCE_DB_PORT', '3306')),
    'user': os.getenv('SOURCE_DB_USER', 'root'),
    'password': os.getenv('SOURCE_DB_PASSWORD', '1234'),
    'database': os.getenv('SOURCE_DB_NAME', 'kopo'),
    'connect_timeout': 30
}

kopo2_DB_CONFIG = {
    'host': os.getenv('TARGET_DB_HOST', '10.98.128.61'),  # target-db-service IP
    'port': int(os.getenv('TARGET_DB_PORT', '3306')),
    'user': os.getenv('TARGET_DB_USER', 'root'),
    'password': os.getenv('TARGET_DB_PASSWORD', '1234'),
    'database': os.getenv('TARGET_DB_NAME', 'kopo2'),
    'connect_timeout': 30
}

def connect_with_retry(config, max_retries=3):
    """데이터베이스 연결 재시도 함수"""
    for i in range(max_retries):
        try:
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor()
            return connection
        except mysql.connector.Error as e:
            if i == max_retries - 1:
                logger.error(f"데이터베이스 연결 실패: {str(e)}")
                raise
            logger.warning(f"데이터베이스 연결 실패, {i+1}번째 재시도...")
            time.sleep(2)

def check_row_count(cursor, table_name):
    """행 개수 검증"""
    try:
        query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(query)
        count = cursor.fetchone()[0]
        logger.info(f"{table_name} 테이블 행 개수: {count}")
        return count
    except mysql.connector.Error as e:
        logger.error(f"{table_name} 테이블 행 개수 검증 실패: {str(e)}")
        raise

def check_aggregation(cursor):
    """집계 검증 - 제품유형별 위해상품 여부 합계"""
    try:
        query = """
        SELECT 
            제품유형,
            COUNT(*) as 총개수,
            SUM(위해상품여부) as 위해상품수
        FROM 위해상품_위험도_분석
        GROUP BY 제품유형
        ORDER BY 위해상품수 DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()
        logger.info("\n제품유형별 위해상품 현황:")
        for row in results:
            logger.info(f"제품유형: {row[0]}, 총개수: {row[1]}, 위해상품수: {row[2]}")
        return results
    except mysql.connector.Error as e:
        logger.error(f"집계 검증 실패: {str(e)}")
        raise

def check_duplicates(cursor):
    """중복 데이터 검증"""
    try:
        query = """
        SELECT 
            doc_no,
            doc_cycl,
            COUNT(*) as count
        FROM 위해상품_위험도_분석
        GROUP BY doc_no, doc_cycl
        HAVING COUNT(*) > 1
        """
        cursor.execute(query)
        duplicates = cursor.fetchall()
        if duplicates:
            logger.warning("\n중복 데이터 발견:")
            for row in duplicates:
                logger.warning(f"doc_no: {row[0]}, doc_cycl: {row[1]}, 중복횟수: {row[2]}")
        else:
            logger.info("\n중복 데이터 없음")
        return duplicates
    except mysql.connector.Error as e:
        logger.error(f"중복 데이터 검증 실패: {str(e)}")
        raise

def check_null_values(cursor):
    """NULL 값 검증"""
    try:
        query = """
        SELECT 
            COUNT(*) as total_rows,
            SUM(CASE WHEN 제품명 IS NULL THEN 1 ELSE 0 END) as null_제품명,
            SUM(CASE WHEN 제조국 IS NULL THEN 1 ELSE 0 END) as null_제조국,
            SUM(CASE WHEN 제품유형 IS NULL THEN 1 ELSE 0 END) as null_제품유형
        FROM 위해상품_위험도_분석
        """
        cursor.execute(query)
        result = cursor.fetchone()
        logger.info("\nNULL 값 검증 결과:")
        logger.info(f"총 행 수: {result[0]}")
        logger.info(f"제품명 NULL 수: {result[1]}")
        logger.info(f"제조국 NULL 수: {result[2]}")
        logger.info(f"제품유형 NULL 수: {result[3]}")
        return result
    except mysql.connector.Error as e:
        logger.error(f"NULL 값 검증 실패: {str(e)}")
        raise

def check_data_range(cursor):
    """데이터 범위 검증 - 위험도등급"""
    try:
        query = """
        SELECT 
            위험도등급,
            COUNT(*) as count
        FROM 위해상품_위험도_분석
        GROUP BY 위험도등급
        """
        cursor.execute(query)
        results = cursor.fetchall()
        logger.info("\n위험도등급 분포:")
        for row in results:
            logger.info(f"등급: {row[0]}, 개수: {row[1]}")
        
        # 허용되지 않은 값 확인
        invalid_query = """
        SELECT COUNT(*)
        FROM 위해상품_위험도_분석
        WHERE 위험도등급 NOT IN ('위험', '주의', '관심', '정상')
        """
        cursor.execute(invalid_query)
        invalid_count = cursor.fetchone()[0]
        if invalid_count > 0:
            logger.warning(f"\n허용되지 않은 위험도등급 발견: {invalid_count}개")
        else:
            logger.info("\n모든 위험도등급이 유효함")
        return results
    except mysql.connector.Error as e:
        logger.error(f"데이터 범위 검증 실패: {str(e)}")
        raise

try:
    # 데이터베이스 연결
    local_connection = connect_with_retry(LOCAL_DB_CONFIG)
    local_cursor = local_connection.cursor()
    logger.info("로컬 데이터베이스 연결 성공")
    
    kopo2_connection = connect_with_retry(kopo2_DB_CONFIG)
    kopo2_cursor = kopo2_connection.cursor()
    logger.info("kopo2 데이터베이스 연결 성공")
    
    # 1. 행 개수 검증
    logger.info("\n=== 행 개수 검증 시작 ===")
    try:
        # 로컬 DB 테이블 검증
        local_counts = {
            '위해상품': check_row_count(local_cursor, 'kopo.위해상품'),
            '위해상품부적합검사': check_row_count(local_cursor, 'kopo.위해상품부적합검사'),
            '위해상품업체': check_row_count(local_cursor, 'kopo.위해상품업체')
        }
        
        # kopo2 DB 테이블 검증
        kopo2_counts = {}
        
        # 위해상품_위험도_분석 테이블이 없으면 생성
        try:
            kopo2_cursor.execute("SELECT COUNT(*) FROM kopo2.위해상품_위험도_분석")
            kopo2_counts['위해상품_위험도_분석'] = check_row_count(kopo2_cursor, 'kopo2.위해상품_위험도_분석')
        except mysql.connector.Error as e:
            if e.errno == 1146:  # Table doesn't exist
                logger.info("위해상품_위험도_분석 테이블이 없어서 생성합니다.")
                kopo2_cursor.execute("""
                    CREATE TABLE kopo2.위해상품_위험도_분석 AS
                    SELECT 
                        w.doc_no,
                        w.doc_cycl,
                        w.prdct_nm as 제품명,
                        w.prdct_type_nm as 제품유형,
                        w.plor_nm as 제조국,
                        w.mnftr_ymd as 제조일자,
                        w.rtl_term_cn as 유통기한,
                        w.safe_cert_no as 안전인증번호,
                        w.prdct_prmsn_no as 제품허가번호,
                        w.rtrvl_rsn_nm as 회수조치내용,
                        w.rtrvl_rsn_cd as 회수조치코드,
                        w.rpt_ymd as 신고일자,
                        w.ntfctn_dt as 통보일자,
                        w.cmd_bgng_dd_cn as 회수시작일,
                        b.icpt_insp_artcl_cn as 부적합검사항목,
                        b.icpt_insp_spcfct_cn as 부적합검사규격,
                        b.icpt_insp_rslt_cn as 부적합검사결과,
                        u.bzenty_type_nm as 업체유형,
                        u.bzenty_nm as 업체명,
                        u.bzenty_brno as 사업자등록번호,
                        u.bzenty_addr as 업체주소,
                        CASE 
                            WHEN w.rtrvl_rsn_cd IS NOT NULL THEN 1
                            ELSE 0
                        END as 위해상품여부,
                        CASE 
                            WHEN w.rtrvl_rsn_cd LIKE '%1%' THEN '위험'
                            WHEN w.rtrvl_rsn_cd LIKE '%2%' THEN '주의'
                            WHEN w.rtrvl_rsn_cd LIKE '%3%' THEN '관심'
                            ELSE '정상'
                        END as 위험도등급
                    FROM kopo.위해상품 w
                    LEFT JOIN kopo.위해상품부적합검사 b 
                        ON w.doc_no = b.doc_no 
                        AND w.doc_cycl = b.doc_cycl
                    LEFT JOIN kopo.위해상품업체 u 
                        ON w.doc_no = u.doc_no 
                        AND w.doc_cycl = u.doc_cycl
                    WHERE w.prdct_nm IS NOT NULL
                        AND w.prdct_type_nm IS NOT NULL
                        AND w.plor_nm IS NOT NULL
                """)
                kopo2_connection.commit()
                logger.info("위해상품_위험도_분석 테이블 생성 완료")
                kopo2_counts['위해상품_위험도_분석'] = check_row_count(kopo2_cursor, 'kopo2.위해상품_위험도_분석')
            else:
                raise
        
        # 위해상품_데이터셋 테이블이 없으면 생성
        try:
            kopo2_cursor.execute("SELECT COUNT(*) FROM kopo2.위해상품_데이터셋")
            kopo2_counts['위해상품_데이터셋'] = check_row_count(kopo2_cursor, 'kopo2.위해상품_데이터셋')
        except mysql.connector.Error as e:
            if e.errno == 1146:  # Table doesn't exist
                logger.info("위해상품_데이터셋 테이블이 없어서 생성합니다.")
                kopo2_cursor.execute("""
                    CREATE TABLE kopo2.위해상품_데이터셋 (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        input_data JSON,
                        output_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                kopo2_connection.commit()
                logger.info("위해상품_데이터셋 테이블 생성 완료")
                kopo2_counts['위해상품_데이터셋'] = check_row_count(kopo2_cursor, 'kopo2.위해상품_데이터셋')
            else:
                raise
        
    except mysql.connector.Error as e:
        logger.error(f"테이블 생성/검증 중 오류 발생: {str(e)}")
        raise
    
    # 2. 집계 검증
    logger.info("\n=== 집계 검증 시작 ===")
    check_aggregation(kopo2_cursor)
    
    # 3. 중복 데이터 검증
    logger.info("\n=== 중복 데이터 검증 시작 ===")
    check_duplicates(kopo2_cursor)
    
    # 4. NULL 값 검증
    logger.info("\n=== NULL 값 검증 시작 ===")
    check_null_values(kopo2_cursor)
    
    # 5. 데이터 범위 검증
    logger.info("\n=== 데이터 범위 검증 시작 ===")
    check_data_range(kopo2_cursor)
    
    # 검증 결과 이력 기록
    insert_history_query = """
        INSERT INTO kopo2.데이터셋_최신화_이력 
        (process_name, status, error_message)
        VALUES (%s, %s, %s)
    """
    kopo2_cursor.execute(insert_history_query, ("데이터 검증", "성공", None))
    kopo2_connection.commit()
    logger.info("\n검증 결과 이력 기록 완료")
    
except Exception as e:
    # 실패 이력 기록
    try:
        insert_history_query = """
            INSERT INTO kopo2.데이터셋_최신화_이력 
            (process_name, status, error_message)
            VALUES (%s, %s, %s)
        """
        kopo2_cursor.execute(insert_history_query, ("데이터 검증", "실패", str(e)))
        kopo2_connection.commit()
    except:
        pass
    logger.error(f"검증 중 오류 발생: {str(e)}")
    raise e
    
finally:
    # 연결 종료
    if 'local_connection' in locals() and local_connection.is_connected():
        local_cursor.close()
        local_connection.close()
        logger.info("로컬 데이터베이스 연결 종료")
    
    if 'kopo2_connection' in locals() and kopo2_connection.is_connected():
        kopo2_cursor.close()
        kopo2_connection.close()
        logger.info("kopo2 데이터베이스 연결 종료")

if __name__ == "__main__":
    main() 
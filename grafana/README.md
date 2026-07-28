# Grafana

Grafana는 MySQL을 직접 조회하며 Gateway의 결제 처리 경로에는 참여하지 않습니다. 데이터 소스와 대시보드는 컨테이너 시작 시 파일에서 자동 프로비저닝됩니다.

## 구성

- 데이터 소스: `provisioning/datasources/mysql.yml`
- 대시보드 공급자: `provisioning/dashboards/default.yml`
- 대시보드: `dashboards/edge-retail-overview.json`
- 기본 대시보드 UID: `edge-retail-overview`

MySQL 데이터 소스는 `GRAFANA_MYSQL_USER`와 `GRAFANA_MYSQL_PASSWORD`를 사용합니다. 이 계정에는 `MYSQL_DATABASE`의 `SELECT` 권한만 부여하며 Gateway 계정이나 MySQL root 계정을 사용하지 않습니다.

## 실행

프로젝트 루트의 `.env`에 다음 값을 설정합니다.

```dotenv
GRAFANA_MYSQL_USER=grafana_reader
GRAFANA_MYSQL_PASSWORD=replace_with_a_real_password
```

새 MySQL 볼륨은 초기화 과정에서 읽기 전용 사용자를 자동 생성합니다. 기존 볼륨에는 사용자 생성 스크립트를 한 번 적용합니다.

```bash
docker compose --env-file .env -f docker-compose.dev.yml up -d --force-recreate mysql
docker compose --env-file .env -f docker-compose.dev.yml exec -T mysql \
  /docker-entrypoint-initdb.d/003_create_grafana_user.sh
docker compose --env-file .env -f docker-compose.dev.yml up -d --force-recreate grafana
```

기본 접속 주소는 `http://localhost:3000/d/edge-retail-overview`입니다. 로그인 계정은 `.env`의 `GRAFANA_ADMIN_USER`와 `GRAFANA_ADMIN_PASSWORD`를 사용합니다.

## 대시보드 패널

1. 누적 결제 건수
2. 누적 판매 금액
3. 상품별 판매 수량
4. 상품별 판매 금액
5. 시간대별 결제 건수
6. 시간대별 판매 금액
7. 최근 결제 목록
8. 평균 상품 인식 confidence
9. 최근 결제의 `payer_track_id`
10. Jetson 상태와 마지막 통신 시각

Gateway는 ISO 8601 시각을 UTC로 정규화해 MySQL `DATETIME(3)`에 저장합니다. Grafana MySQL 세션도 `+00:00`으로 설정하고 화면 표시는 브라우저 시간대를 사용합니다.

## 권한 확인

MySQL 관리 계정에서 다음 명령으로 부여된 권한을 확인할 수 있습니다.

```sql
SHOW GRANTS FOR 'grafana_reader'@'%';
```

결과에는 대상 데이터베이스의 `SELECT`만 있어야 합니다. 대시보드 편집 결과는 파일 프로비저닝에 의해 덮어쓰일 수 있으므로 변경 사항은 JSON 파일에 반영합니다.

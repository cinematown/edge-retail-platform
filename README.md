# Edge Retail Platform

Jetson YOLO가 발행한 무인매장 결제 완료 이벤트를 Raspberry Pi의 Gateway가 처리해 MySQL에 저장하고, Grafana에서 판매 현황을 조회하는 1차 MVP 프로젝트입니다.

## 범위

이 저장소는 다음 구성 요소를 다룹니다.

- Eclipse Mosquitto 개발 및 배포 설정
- Python 기반 Edge Gateway 기준 구현
- Java 21 + Micronaut 기반 Edge Gateway 재구현
- 재현 가능한 시나리오를 사용하는 Mock YOLO Publisher
- MySQL 스키마와 초기 상품 데이터
- Grafana MySQL 데이터 소스와 대시보드
- Raspberry Pi용 systemd 및 Mosquitto 배포 설정

YOLO 탐지·추적 코드, 실제 고객 신원 확인, 금융 결제, 카드 연동, 영수증 발급과 전체 재고 시스템은 이 저장소의 범위가 아닙니다.

## 처리 구조

```text
Jetson YOLO Publisher
        │ MQTT
        ▼
Eclipse Mosquitto
        │
        ▼
Edge Gateway Service
  ├─ 메시지 파싱 및 검증
  ├─ 중복 eventId 방지
  ├─ MySQL 상품 가격 조회
  └─ 결제 및 상품 내역 트랜잭션 저장
        │
        ▼
MySQL ◀── Grafana
```

Gateway의 MQTT Subscriber는 별도 서비스로 분리하지 않습니다. Jetson은 가격을 발행하지 않으며, Gateway가 `products` 테이블의 단가로 결제 금액을 계산합니다.

## 고정 MQTT 계약

1차 Gateway MVP에서 처리할 필수 토픽은 다음과 같습니다.

```text
retail/jetson-01/checkout/completed
retail/jetson-01/status
```

선택 토픽은 다음과 같습니다.

```text
retail/jetson-01/cart/state
```

결제 이벤트의 `schemaVersion`은 `1`입니다. 추적 객체는 Jetson 재시작 후 ID가 재사용될 수 있으므로 `trackingSessionId`와 각 track ID의 조합으로 구분합니다.

## 디렉터리

```text
edge-retail-platform/
├── README.md
├── .env.example
├── docker-compose.dev.yml
├── docs/
├── gateway/                    # Python 기준 구현
│   ├── src/edge_gateway/
│   └── tests/
├── gateway-micronaut/          # Java 21 재구현
│   ├── src/main/java/
│   ├── src/test/java/
│   └── README.md
├── mock-publisher/
│   ├── scenarios/
│   └── payloads/
├── database/
│   ├── 001_schema.sql
│   ├── 002_seed_products.sql
│   └── 003_create_grafana_user.sh
├── grafana/
│   ├── provisioning/
│   └── dashboards/
└── deployment/
    ├── edge-gateway-micronaut.service
    └── mosquitto/
        └── mosquitto.dev.conf
```

## 환경 변수

로컬 설정 파일을 준비할 때 예제 파일을 복사하고 실제 비밀번호로 변경합니다.

```bash
cp .env.example .env
```

`.env`는 Git에 포함하지 않습니다. 비밀번호와 전체 DB 접속 문자열도 로그에 출력하지 않습니다.

## 개발용 인프라

Docker Engine과 Docker Compose 플러그인이 설치된 개발 환경에서 다음 명령으로 Mosquitto, MySQL 8, Grafana를 실행합니다.

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.dev.yml config --quiet
docker compose --env-file .env -f docker-compose.dev.yml up -d
docker compose --env-file .env -f docker-compose.dev.yml ps
```

기본 접속 지점은 다음과 같습니다.

| 구성 요소 | 접속 지점 |
|---|---|
| Mosquitto | `localhost:1883` |
| MySQL | `localhost:3306` |
| Grafana | `http://localhost:3000` |

Mosquitto는 익명 접속을 허용하지 않습니다. `.env`의 `MQTT_USERNAME`과 `MQTT_PASSWORD`를 사용해야 합니다. MySQL은 최초로 빈 볼륨을 초기화할 때 스키마, 상품 시드, Grafana 읽기 전용 사용자 생성을 순서대로 적용합니다.

개발용 포트는 모두 로컬 개발 환경에만 노출되도록 설정합니다. 기본 포트가 이미 사용 중이면 `.env`의 해당 포트 값을 변경한 뒤 Compose 명령을 실행합니다.

서비스를 중지하되 데이터를 보존하려면 다음 명령을 사용합니다.

```bash
docker compose --env-file .env -f docker-compose.dev.yml down
```

`down --volumes`는 MySQL과 Grafana를 포함한 개발 데이터를 삭제하므로 초기화가 명확히 필요한 경우에만 사용합니다.

## Mock Publisher

Mock Publisher는 임의 데이터를 생성하지 않고 `mock-publisher/scenarios/`의 고정 시나리오를 순서대로 재생합니다. 프로젝트 루트의 `.env`를 자동으로 읽으며, `"AUTO"` 값은 발행 시점의 timezone 포함 ISO 8601 시각으로 바뀝니다.

Ubuntu에서 Python 가상환경과 의존성을 준비한 뒤 원하는 시나리오를 실행합니다.

```bash
sudo apt-get install -y python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r mock-publisher/requirements.txt
.venv/bin/python mock-publisher/publisher.py \
  mock-publisher/scenarios/normal-multiple-items.json
```

제공 시나리오는 정상 단일상품, 정상 복수상품, 동일 이벤트 중복, 빈 장바구니, 존재하지 않는 SKU입니다. 상세 사용법과 CLI 옵션은 `mock-publisher/README.md`를 참고합니다.

## Gateway 구현

두 구현은 같은 MQTT 계약, MySQL 스키마, 중복 처리 정책과 Grafana 대시보드를 공유합니다. 비교 또는 통합 검증 시에는 두 게이트웨이를 동시에 실행하지 않습니다.

### Python 기준 구현

Python Gateway는 MQTT Subscriber를 내부에 포함한 단일 프로세스입니다. checkout 메시지를 Pydantic으로 검증하고 MySQL에서 상품 단가를 조회한 뒤, `checkouts`와 `checkout_items`를 하나의 트랜잭션으로 저장합니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e gateway
.venv/bin/edge-gateway
```

구조와 테스트 명령은 `gateway/README.md`를 참고합니다.

### Micronaut Java 구현

Micronaut Gateway는 Java 21 기반 비웹 프로세스입니다. Micronaut MQTT가 Mosquitto 구독과 재연결을 담당하고, Serialization·Validation이 메시지 계약을 검사하며, Micronaut Data JDBC와 HikariCP가 MySQL 연결 및 트랜잭션 수명주기를 관리합니다. JPA와 Hibernate는 사용하지 않습니다.

```bash
cd gateway-micronaut
set -a
source ../.env
set +a
gradle run
```

배포용 실행 디렉터리는 다음과 같이 생성합니다.

```bash
gradle test installDist
./build/install/edge-retail-gateway-micronaut/bin/edge-retail-gateway-micronaut
```

세부 실행법과 검증 절차는 `gateway-micronaut/README.md`를 참고합니다.

두 구현 모두 `completedAt`을 UTC로 정규화해 MySQL `DATETIME(3)`에 저장하고, 동일한 `eventId` 재전송을 중복 거래로 저장하지 않습니다. 검증 실패나 MySQL 오류는 해당 메시지만 실패시키며 게이트웨이 프로세스는 계속 실행됩니다.

## 데이터베이스 초기화

MySQL 8.x 관리 계정으로 스키마와 초기 데이터를 순서대로 적용합니다.

```bash
mysql -u root -p < database/001_schema.sql
mysql -u root -p < database/002_seed_products.sql
```

초기 상품 데이터는 다음 네 SKU를 포함합니다.

| SKU | 상품명 | 단가(원) |
|---|---|---:|
| `cola_can` | 콜라 캔 | 1,500 |
| `water_bottle` | 생수 | 1,000 |
| `snack_red` | 빨간 과자 | 2,000 |
| `snack_blue` | 파란 과자 | 2,200 |

스키마 적용 후 다음 쿼리로 확인할 수 있습니다.

```sql
USE edge_retail;
SHOW TABLES;
SELECT sku, product_name, unit_price, is_active
FROM products
ORDER BY sku;
```

## Grafana

Grafana는 `Edge Retail MySQL` 데이터 소스와 `Edge Retail Overview` 대시보드를 시작 시 자동 프로비저닝합니다. MySQL 연결에는 대상 DB의 `SELECT` 권한만 가진 `GRAFANA_MYSQL_USER`를 사용합니다.

기본 대시보드 주소는 `http://localhost:3000/d/edge-retail-overview`입니다.

기존 MySQL 개발 볼륨에 읽기 계정을 처음 적용할 때는 다음 명령을 한 번 실행합니다. 새 볼륨에서는 초기화 과정에 자동 실행됩니다.

```bash
docker compose --env-file .env -f docker-compose.dev.yml up -d --force-recreate mysql
docker compose --env-file .env -f docker-compose.dev.yml exec -T mysql /docker-entrypoint-initdb.d/003_create_grafana_user.sh
docker compose --env-file .env -f docker-compose.dev.yml up -d --force-recreate grafana
```

대시보드는 누적 결제 건수·판매 금액, 상품별 수량·금액, 시간대별 결제·매출, 최근 결제, 평균 confidence, 최근 payer track ID, Jetson 상태를 표시합니다. 세부 구성과 권한 확인 방법은 `grafana/README.md`를 참고합니다.

## 자동 검증

Micronaut Gateway GitHub Actions는 다음을 실제로 검증합니다.

1. Java 21에서 단위 테스트 및 `installDist` 패키징
2. Docker 기반 Mosquitto와 MySQL 실행
3. Micronaut Gateway 시작
4. 기존 정상 복수상품 및 중복 이벤트 Mock Publisher 시나리오 발행
5. 정상 결제의 상품 수 3개와 총액 5,000원 확인
6. 동일 `eventId`가 한 건만 저장되는지 확인
7. Jetson ONLINE 상태가 `device_status`에 반영되는지 확인

## 구현 단계

- [x] 1단계: 프로젝트 골격, 환경 변수 예시, README 초안, DB 스키마/시드
- [x] 2단계: 개발용 Mosquitto, MySQL, Grafana 인프라
- [x] 3단계: 시나리오 기반 Mock Publisher
- [x] 4단계: Python Gateway 기본 결제 처리
- [x] 5단계: 중복·검증·DB 오류와 MQTT 재연결 처리
- [x] 6단계: Grafana 프로비저닝과 대시보드
- [x] 7단계: Micronaut Java Gateway 재구현과 자동 end-to-end 검증
- [ ] 8단계: 실제 Jetson Publisher 통합 및 현장 end-to-end 검증

Docker Compose는 개발 및 자동 검증 환경에 사용합니다. Raspberry Pi의 최종 프로세스는 Mosquitto, Gateway, MySQL, Grafana를 독립 서비스로 운영합니다. HeatWave 연동은 2차 MVP이고 로컬 결제 경로에는 포함하지 않습니다.

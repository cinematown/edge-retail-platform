# Micronaut Gateway

기존 `gateway/` Python 구현과 동일한 MQTT 계약과 MySQL 스키마를 사용하는 Java 21 기반 게이트웨이입니다. Python 구현은 기준 구현으로 유지하며, 두 게이트웨이를 동시에 같은 topic과 DB에 연결하지 않습니다.

## 구성

- Micronaut MQTT v3: Mosquitto 구독과 자동 재연결
- Micronaut Serialization + Validation: JSON 역직렬화와 계약 검증
- Micronaut Data JDBC + HikariCP: MySQL 연결과 트랜잭션
- MySQL Connector/J

JPA와 Hibernate, HTTP 서버는 사용하지 않습니다.

## 처리 topic

```text
retail/jetson-01/checkout/completed
retail/jetson-01/status
```

## 실행

먼저 저장소 루트에서 개발 인프라를 실행합니다.

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.dev.yml up -d
```

Micronaut는 운영체제 환경 변수를 읽습니다. `.env`를 현재 셸에 export한 뒤 실행합니다.

```bash
cd gateway-micronaut
set -a
source ../.env
set +a
sh ./gradlew run
```

최초 실행 시 `gradlew`가 Gradle 공식 배포 서버에서 wrapper JAR을 내려받고 SHA-256을 확인합니다. Gradle이 시스템에 설치되어 있다면 `gradle run`도 사용할 수 있습니다.

다른 터미널에서 기존 Mock Publisher를 실행합니다.

```bash
.venv/bin/python mock-publisher/publisher.py \
  mock-publisher/scenarios/normal-multiple-items.json
```

정상 복수상품 시나리오는 기존 Python Gateway와 동일하게 상품 수 3개, 총액 5,000원으로 저장되어야 합니다.

## 검증 시나리오

Python Gateway를 중지한 상태에서 다음 기존 시나리오를 순서대로 실행합니다.

```bash
.venv/bin/python mock-publisher/publisher.py mock-publisher/scenarios/normal-single-item.json
.venv/bin/python mock-publisher/publisher.py mock-publisher/scenarios/normal-multiple-items.json
.venv/bin/python mock-publisher/publisher.py mock-publisher/scenarios/duplicate-event.json
.venv/bin/python mock-publisher/publisher.py mock-publisher/scenarios/empty-cart.json
.venv/bin/python mock-publisher/publisher.py mock-publisher/scenarios/invalid-sku.json
```

확인 항목:

- 정상 결제는 `checkouts`, `checkout_items`에 하나의 트랜잭션으로 저장됨
- 동일 `eventId`는 한 번만 저장됨
- 빈 장바구니와 잘못된 SKU는 저장되지 않음
- status 메시지는 `device_status`를 upsert함
- 기존 Grafana 대시보드는 변경 없이 저장 결과를 조회함

## 로그 이벤트

```text
MESSAGE_RECEIVED
MESSAGE_VALIDATION_FAILED
CHECKOUT_PROCESSED
CHECKOUT_DUPLICATE_SKIPPED
UNKNOWN_SKU
DATABASE_ERROR
MESSAGE_HANDLER_ERROR
DEVICE_STATUS_UPDATED
```

원본 MQTT payload와 비밀번호는 로그에 남기지 않습니다.

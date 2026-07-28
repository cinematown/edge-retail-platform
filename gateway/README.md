# Edge Gateway Service

MQTT Subscriber, 메시지 검증, 상품 가격 조회와 MySQL 저장을 하나의 Python 프로세스에서 실행합니다.

## 처리 흐름

```text
retail/jetson-01/checkout/completed
→ Pydantic JSON 계약 검증
→ MySQL products 단가 조회
→ 수량·소계·총액 계산
→ checkouts와 checkout_items INSERT
→ commit
```

가격 조회부터 두 테이블 저장까지 하나의 MySQL 트랜잭션입니다. 처리 중 예외가 발생하면 rollback합니다. `completedAt`은 UTC offset이 있는 값만 허용하며, MySQL의 timezone 없는 `DATETIME(3)`에는 UTC로 변환해 저장합니다.

## 실행

프로젝트 루트에서 `.env`와 개발용 인프라를 준비합니다.

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.dev.yml up -d
python3 -m venv .venv
.venv/bin/python -m pip install -e gateway
.venv/bin/edge-gateway
```

Gateway는 기본적으로 다음 topic을 QoS 1로 구독합니다.

```text
retail/jetson-01/checkout/completed
retail/jetson-01/status
```

접속 정보와 비밀번호는 프로젝트 루트의 `.env`에서 읽습니다. 실제 프로세스 환경 변수는 `.env`보다 우선하며 비밀번호나 전체 DB 접속 문자열은 로그에 출력하지 않습니다.

## 중복과 장애 처리

- 처리된 `eventId`는 상품 가격 조회 전에 건너뜁니다.
- 동시에 같은 이벤트가 들어오는 경우 DB의 `UNIQUE(event_id)`를 최종 방어선으로 사용합니다.
- 빈 `items`, 잘못된 schema, 알 수 없는 SKU는 거래를 저장하지 않습니다.
- checkout 저장 실패는 전체 rollback하며 MQTT 콜백과 Gateway 프로세스는 유지됩니다.
- MQTT 연결이 끊기면 1초부터 최대 30초까지 지수 backoff로 재연결하고 두 topic을 다시 구독합니다.
- status 메시지는 `device_status`에 device별 insert 또는 update됩니다.

## 테스트

```bash
.venv/bin/python -m unittest discover -s gateway/tests -p "test_*.py" -v
```

테스트는 계약 검증, 가격 계산, UTC 변환, 중복 선조회, status upsert, 트랜잭션 commit과 rollback을 확인합니다.

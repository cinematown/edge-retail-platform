# Mock YOLO Publisher

Gateway 개발과 검증을 위해 Jetson YOLO의 MQTT 메시지를 재현 가능한 순서로 발행합니다. 랜덤 값은 만들지 않으며 시나리오 파일에 정의된 topic, 지연 시간, payload를 그대로 사용합니다.

d## 준비

프로젝트 루트에서 실행합니다.

```bash
sudo apt-get install -y python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r mock-publisher/requirements.txt
cp .env.example .env
```

`.env`의 MQTT 접속 정보를 실제 개발 Broker에 맞게 설정합니다. `MQTT_USERNAME`과 `MQTT_PASSWORD`는 함께 지정해야 하며 로그에는 비밀번호가 출력되지 않습니다.

## 실행

```bash
.venv/bin/python mock-publisher/publisher.py \
  mock-publisher/scenarios/normal-single-item.json
```

기본 QoS는 `1`이고 메시지는 retain하지 않습니다. 각 payload의 정확한 문자열 값 `"AUTO"`는 메시지를 발행할 때 timezone과 millisecond를 포함한 ISO 8601 시각으로 재귀적으로 치환됩니다.

주요 옵션은 다음과 같습니다.

```text
--env-file PATH
--host HOST
--port PORT
--username USERNAME
--password PASSWORD
--client-id CLIENT_ID
--qos {0,1,2}
--timeout SECONDS
```

CLI 옵션은 `.env` 값보다 우선합니다. 전체 옵션은 다음 명령으로 확인합니다.

```bash
.venv/bin/python mock-publisher/publisher.py --help
```

## 시나리오

| 파일 | 목적 |
|---|---|
| `normal-single-item.json` | `cola_can` 1개 정상 결제와 ONLINE 상태 |
| `normal-multiple-items.json` | `cola_can` 2개와 `snack_red` 1개 정상 결제 |
| `duplicate-event.json` | 같은 `eventId`와 `checkoutId`를 두 번 발행 |
| `empty-cart.json` | 빈 `items` 검증 실패 확인 |
| `invalid-sku.json` | `unknown_product` 검증 실패 확인 |

시나리오 파일의 루트는 비어 있지 않은 JSON 배열이어야 합니다. 각 단계는 다음 필드를 가집니다.

```json
{
  "delayMs": 0,
  "topic": "retail/jetson-01/checkout/completed",
  "payload": {
    "schemaVersion": 1
  }
}
```

`delayMs`는 0 이상의 정수이며 이전 단계가 발행된 뒤 기다릴 시간입니다.

## 테스트

```bash
.venv/bin/python -m unittest discover \
  -s mock-publisher/tests \
  -p "test_*.py"
```

Mosquitto CLI가 있으면 별도 터미널에서 실제 발행 내용을 확인할 수 있습니다.

```bash
mosquitto_sub \
  -h "${MQTT_HOST:-localhost}" \
  -p "${MQTT_PORT:-1883}" \
  -u "$MQTT_USERNAME" \
  -P "$MQTT_PASSWORD" \
  -t "retail/jetson-01/#" \
  -v
```

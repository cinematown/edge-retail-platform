#!/usr/bin/env python3
"""Replay deterministic Jetson MQTT scenarios for Gateway development."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


class ScenarioError(ValueError):
    """Raised when a scenario file does not match the replay format."""


def emit_log(event: str, **fields: Any) -> None:
    record = {"event": event, **fields}
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)


def current_iso_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def replace_auto(value: Any, timestamp: str) -> Any:
    """Return a copy with every exact string value AUTO replaced."""
    if value == "AUTO":
        return timestamp
    if isinstance(value, list):
        return [replace_auto(item, timestamp) for item in value]
    if isinstance(value, dict):
        return {key: replace_auto(item, timestamp) for key, item in value.items()}
    return value


def load_scenario(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScenarioError(f"scenario file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioError(
            f"invalid scenario JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc

    if not isinstance(raw, list) or not raw:
        raise ScenarioError("scenario root must be a non-empty JSON array")

    for index, step in enumerate(raw, start=1):
        if not isinstance(step, dict):
            raise ScenarioError(f"step {index} must be an object")

        delay_ms = step.get("delayMs")
        if (
            isinstance(delay_ms, bool)
            or not isinstance(delay_ms, int)
            or delay_ms < 0
        ):
            raise ScenarioError(f"step {index} delayMs must be a non-negative integer")

        topic = step.get("topic")
        if not isinstance(topic, str) or not topic.strip():
            raise ScenarioError(f"step {index} topic must be a non-empty string")

        if not isinstance(step.get("payload"), dict):
            raise ScenarioError(f"step {index} payload must be an object")

    return raw


def build_parser(default_env_file: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay a deterministic JSON scenario to an MQTT broker."
    )
    parser.add_argument("scenario", type=Path, help="scenario JSON file to replay")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=default_env_file,
        help=f"environment file (default: {default_env_file})",
    )
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"))
    parser.add_argument(
        "--client-id",
        default=os.getenv("MOCK_MQTT_CLIENT_ID", "mock-yolo-publisher-01"),
    )
    parser.add_argument("--qos", type=int, choices=(0, 1, 2), default=1)
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    pre_args, _ = pre_parser.parse_known_args(argv)
    load_dotenv(pre_args.env_file, override=False)

    parser = build_parser(pre_args.env_file)
    args = parser.parse_args(argv)
    if bool(args.username) != bool(args.password):
        parser.error("MQTT username and password must be provided together")
    if not 1 <= args.port <= 65535:
        parser.error("MQTT port must be between 1 and 65535")
    if args.timeout <= 0:
        parser.error("timeout must be greater than zero")
    return args


def replay_scenario(args: argparse.Namespace) -> None:
    steps = load_scenario(args.scenario)
    connected = threading.Event()
    connection_error: list[str] = []

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=args.client_id,
        protocol=mqtt.MQTTv311,
    )
    if args.username:
        client.username_pw_set(args.username, args.password)

    def on_connect(
        _client: mqtt.Client,
        _userdata: Any,
        _flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code == 0:
            emit_log(
                "MQTT_CONNECTED",
                host=args.host,
                port=args.port,
                client_id=args.client_id,
            )
        else:
            connection_error.append(str(reason_code))
        connected.set()

    client.on_connect = on_connect
    loop_started = False
    try:
        connect_result = client.connect(args.host, args.port, keepalive=60)
        if connect_result != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(mqtt.error_string(connect_result))

        client.loop_start()
        loop_started = True
        if not connected.wait(args.timeout):
            raise TimeoutError("timed out waiting for MQTT CONNACK")
        if connection_error:
            raise ConnectionError(f"MQTT connection rejected: {connection_error[0]}")

        for index, step in enumerate(steps, start=1):
            time.sleep(step["delayMs"] / 1000)
            timestamp = current_iso_timestamp()
            payload = replace_auto(step["payload"], timestamp)
            encoded = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")

            publish_result = client.publish(
                step["topic"], payload=encoded, qos=args.qos, retain=False
            )
            if publish_result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(mqtt.error_string(publish_result.rc))
            publish_result.wait_for_publish(timeout=args.timeout)
            if not publish_result.is_published():
                raise TimeoutError(f"publish timeout at step {index}")

            emit_log(
                "MOCK_MESSAGE_PUBLISHED",
                step=index,
                topic=step["topic"],
                qos=args.qos,
                event_id=payload.get("eventId"),
                checkout_id=payload.get("checkoutId"),
                device_id=payload.get("deviceId"),
            )

        emit_log(
            "SCENARIO_COMPLETED",
            scenario=str(args.scenario),
            message_count=len(steps),
        )
    finally:
        if loop_started:
            client.disconnect()
            client.loop_stop()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        replay_scenario(args)
    except (OSError, ScenarioError, ValueError, RuntimeError) as exc:
        emit_log("MOCK_PUBLISH_FAILED", error_type=type(exc).__name__, message=str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

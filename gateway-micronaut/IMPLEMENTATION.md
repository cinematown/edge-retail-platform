# 구현 메모

기존 Python Gateway와 다음 외부 계약을 공유합니다.

- MQTT topic과 JSON 필드
- MySQL 테이블과 인덱스
- `eventId` 멱등성 정책
- UTC 정규화 규칙
- Grafana 조회 구조

Micronaut 버전에서 프레임워크에 위임한 책임은 다음과 같습니다.

- MQTT 연결과 자동 재연결
- JSON 역직렬화
- Bean Validation
- HikariCP 연결 풀
- JDBC 연결 수명주기
- 선언적 트랜잭션

직접 구현한 책임은 상품 가격 조회, 합계 계산, 미등록 SKU 거부, 중복 이벤트 처리와 구조화 로그입니다.

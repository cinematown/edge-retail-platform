#!/bin/bash
set -euo pipefail

: "${MYSQL_DATABASE:?MYSQL_DATABASE is required}"
: "${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is required}"
: "${GRAFANA_MYSQL_USER:?GRAFANA_MYSQL_USER is required}"
: "${GRAFANA_MYSQL_PASSWORD:?GRAFANA_MYSQL_PASSWORD is required}"

case "$MYSQL_DATABASE" in
  *[!A-Za-z0-9_]*|'')
    echo "MYSQL_DATABASE must contain only letters, numbers, and underscores" >&2
    exit 1
    ;;
esac

case "$GRAFANA_MYSQL_USER" in
  *[!A-Za-z0-9_]*|'')
    echo "GRAFANA_MYSQL_USER must contain only letters, numbers, and underscores" >&2
    exit 1
    ;;
esac

escaped_password=${GRAFANA_MYSQL_PASSWORD//\\/\\\\}
escaped_password=${escaped_password//\'/\'\'}

mysql --protocol=socket -uroot -p"$MYSQL_ROOT_PASSWORD" <<SQL
CREATE USER IF NOT EXISTS '${GRAFANA_MYSQL_USER}'@'%' IDENTIFIED BY '${escaped_password}';
ALTER USER '${GRAFANA_MYSQL_USER}'@'%' IDENTIFIED BY '${escaped_password}';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '${GRAFANA_MYSQL_USER}'@'%';
GRANT SELECT ON \`${MYSQL_DATABASE}\`.* TO '${GRAFANA_MYSQL_USER}'@'%';
SQL

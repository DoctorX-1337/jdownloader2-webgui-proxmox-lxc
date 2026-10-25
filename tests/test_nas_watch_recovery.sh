#!/bin/bash
set -euo pipefail

source_script=${1:-"$(cd "$(dirname "$0")/.." && pwd)/scripts/nas-watch.sh"}
test_dir=$(mktemp -d /tmp/jd-nas-watch-test.XXXXXX)
cleanup() {
  rm -f "$test_dir/timeout" "$test_dir/systemctl" "$test_dir/logger" "$test_dir/run.sh" "$test_dir/events" "$test_dir/blocked"
  rmdir "$test_dir"
}
trap cleanup EXIT

sed "s#/run/jdownloader-nas-blocked#$test_dir/blocked#g" "$source_script" > "$test_dir/run.sh"
cat > "$test_dir/timeout" <<'STUB'
#!/bin/sh
test "$TEST_HEALTHY" = 1
STUB
cat > "$test_dir/systemctl" <<'STUB'
#!/bin/sh
printf '%s\n' "$1" >> "$TEST_EVENTS"
test -f "$TEST_MARKER" || exit 67
if [ "$1" = stop ]; then exit 9; fi
STUB
cat > "$test_dir/logger" <<'STUB'
#!/bin/sh
exit 0
STUB
chmod 0700 "$test_dir/timeout" "$test_dir/systemctl" "$test_dir/logger"
export TEST_MARKER="$test_dir/blocked" TEST_EVENTS="$test_dir/events"
export PATH="$test_dir:$PATH"

set +e
TEST_HEALTHY=0 bash "$test_dir/run.sh"
failed_stop=$?
set -e
test "$failed_stop" -eq 9
test -f "$TEST_MARKER"
TEST_HEALTHY=1 bash "$test_dir/run.sh"
test ! -f "$TEST_MARKER"
test "$(cat "$TEST_EVENTS")" = $'stop\nstart'
echo 'NAS_WATCH_RECOVERY_TEST_OK'

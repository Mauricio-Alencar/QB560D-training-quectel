#!/bin/sh
set -eu
QAI_TEST_ROOT=/tmp/qairt-isolated-20261101T020546Z
test "$QAI_TEST_ROOT" = /tmp/qairt-isolated-20261101T020546Z
test ! -L "$QAI_TEST_ROOT"
test "$(readlink -f "$QAI_TEST_ROOT")" = "$QAI_TEST_ROOT"
test -f "$QAI_TEST_ROOT/test-ownership.json"
grep -q '"session": "20261101T020546Z"' "$QAI_TEST_ROOT/test-ownership.json"
if ps -eo args | grep -F "$QAI_TEST_ROOT/bin/tiny_graph" | grep -v grep >/dev/null; then
  printf 'Refusing cleanup while the isolated graph is running.\n' >&2
  exit 1
fi
cd /tmp
rm -rf -- "$QAI_TEST_ROOT"
printf 'Removed only %s\n' "$QAI_TEST_ROOT"


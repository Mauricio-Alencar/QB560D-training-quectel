#!/bin/sh
set -eu
QAI_TEST_ROOT=/tmp/qairt-isolated-20261101T020546Z
test -f "$QAI_TEST_ROOT/test-ownership.json"
exec env LD_LIBRARY_PATH="$QAI_TEST_ROOT/lib:/usr/lib:/lib/aarch64-linux-gnu:/usr/lib/aarch64-linux-gnu" ADSP_LIBRARY_PATH="$QAI_TEST_ROOT/dsp;/usr/lib/rfsa/adsp;/dsp;/usr/lib" /usr/bin/timeout 25s "$QAI_TEST_ROOT/bin/tiny_graph" "$QAI_TEST_ROOT/lib/libQnnHtp.so"


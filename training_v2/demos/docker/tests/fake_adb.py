"""Local protocol simulator: never connects to hardware and uses dummy credentials."""
import base64
import os
import re
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

mode = os.environ.get('FAKE_ADB_MODE', 'login')
secret = 'dummy-test-password'


def emit(text):
    sys.stdout.write(text)
    sys.stdout.flush()


if mode != 'direct':
    emit('test-box login: ')
    user = sys.stdin.readline().strip()
    emit('Password: ')
    password = sys.stdin.readline().strip()
    if user != 'root' or password != secret:
        emit('\nLogin incorrect\n')
        raise SystemExit(1)
emit('\nroot@test-box:~# ')
pending = None
for line in sys.stdin:
    if line.strip() == 'exit':
        break
    uid = re.search(r'(__QB_UID_[0-9a-f]+__)', line)
    if uid:
        emit('\n' + uid.group(1) + '=' + ('1000' if mode == 'nonroot' else '0') + '\n')
        continue
    begin = re.search(r'(__QB_CMD_[0-9a-f]+___BEGIN)', line)
    if begin:
        emit('\n' + begin.group(1) + '\n')
        continue
    delimiter = re.search(r"base64 -d <<'([^']+)'", line)
    if delimiter:
        payload = []
        for part in sys.stdin:
            if part.strip() == delimiter.group(1):
                break
            payload.append(part)
        pending = base64.b64decode(''.join(payload)).decode('utf-8')
        continue
    end = re.search(r'(__QB_CMD_[0-9a-f]+___END)', line)
    if end:
        status = 0
        if pending == 'CASE_TIMEOUT':
            time.sleep(10)
        elif pending == 'CASE_EXIT_7':
            emit('failure is preserved\n')
            status = 7
        elif pending == 'CASE_PROMPTS_IN_OUTPUT':
            emit('login:\nPassword:\n')
        elif pending == 'CASE_SECRET_OUTPUT':
            emit(secret + '\n')
        else:
            emit('RESULT:' + pending + '\n')
        emit('\n' + end.group(1) + '=' + str(status) + '\n')
        pending = None

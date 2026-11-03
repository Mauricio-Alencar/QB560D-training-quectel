"""Portable ADB selection and a root shell that handles the BSP's login prompt.

The Linux password travels only through adb shell stdin, after Password: appears.
It is never part of argv, a command receipt, or a file in the training package.
"""
import atexit
import base64
import getpass
import os
from pathlib import Path
from pathlib import PurePosixPath
import queue
import re
import shutil
import subprocess
import sys
import threading
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
_SESSIONS = {}
_ANSI = re.compile(rb'\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))')
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')


class AuthenticationError(RuntimeError):
    pass


def local_path(value):
    """Use the Windows extended path form for local copies, without passing it to adb."""
    path = Path(value).absolute()
    text = str(path)
    if os.name == 'nt' and not text.startswith('\\\\?\\'):
        text = '\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\') else '\\\\?\\' + text
        return Path(text)
    return path


def transfer_files(base, action, source, destination, **kwargs):
    """Copy files for an already authenticated transport, including long Windows paths."""
    if action not in ('push', 'pull'):
        raise ValueError('Only ADB push/pull transfers are supported')
    check, timeout = kwargs.pop('check', True), kwargs.pop('timeout', 180)
    if os.name != 'nt':
        return subprocess.run(list(base) + [action, str(source), str(destination)], check=check, timeout=timeout, **kwargs)
    # Keep the paths passed to Windows ADB short. Python handles the local copy
    # through extended paths, while the temporary directory has its own lifetime.
    with tempfile.TemporaryDirectory(prefix='qb-adb-') as temporary:
        temp = Path(temporary).resolve()
        if temp.parent != Path(tempfile.gettempdir()).resolve():
            raise RuntimeError('Unexpected temporary transfer directory')
        if action == 'push':
            local = local_path(source)
            staged = temp / local.name
            if local.is_dir():
                shutil.copytree(local, staged)
            else:
                shutil.copy2(local, staged)
            return subprocess.run(list(base) + ['push', str(staged), str(destination)], check=check, timeout=timeout, **kwargs)
        staged = temp / 'payload'
        result = subprocess.run(list(base) + ['pull', str(source), str(staged)], check=check, timeout=timeout, **kwargs)
        if result.returncode == 0:
            local = local_path(destination)
            if local.is_dir():
                local /= PurePosixPath(str(source).rstrip('/')).name
            local.parent.mkdir(parents=True, exist_ok=True)
            if staged.is_dir():
                shutil.copytree(staged, local, dirs_exist_ok=True)
            else:
                shutil.copy2(staged, local)
        return result


def resolve_adb(value=None):
    requested = value or os.environ.get('QB560D_ADB')
    if requested in ('adb', 'adb.exe') and not shutil.which(requested):
        requested = None
    if requested:
        candidate = Path(requested).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(str(requested))
        if found:
            return found
        raise FileNotFoundError('ADB not found. Supply --adb with your platform-tools executable.')
    bundled = ROOT / 'tools/platform-tools/adb.exe'
    if os.name == 'nt' and bundled.is_file():
        return str(bundled)
    found = shutil.which('adb')
    if found:
        return found
    raise FileNotFoundError('ADB not found in the package or PATH. Supply --adb explicitly.')


def select_device(adb=None, serial=None, transport_id=None):
    executable = resolve_adb(adb)
    output = subprocess.check_output([executable, 'devices', '-l'], text=True, timeout=15)
    rows = []
    for line in output.splitlines()[1:]:
        fields = line.split()
        if len(fields) > 1 and fields[1] == 'device':
            details = dict(v.split(':', 1) for v in fields[2:] if ':' in v)
            rows.append({'serial': fields[0], **details})
    if serial is not None:
        rows = [row for row in rows if row['serial'] == serial]
    if transport_id is not None:
        rows = [row for row in rows if row.get('transport_id') == str(transport_id)]
    if len(rows) != 1:
        raise ValueError('Select one authorized box. With multiple boxes use --serial or --transport-id; serial ? may be repeated.')
    identity = rows[0]
    selection = ['-t', identity['transport_id']] if identity.get('transport_id') else ['-s', identity['serial']]
    return [executable, *selection], identity


class AdbSession:
    def __init__(self, adb=None, serial=None, transport_id=None, user=None, password=None,
                 password_provider=None, base=None, identity=None):
        if base is None:
            self.base, self.identity = select_device(adb, serial, transport_id)
        else:
            self.base, self.identity = list(base), identity or {'selection': list(base)[1:]}
        self.user = user or os.environ.get('QB560D_ADB_USER', 'root')
        self._password = password
        self._provider = password_provider
        self._process = None
        self._queue = queue.Queue()
        self._buffer = b''
        self.auth = {'user': self.user, 'login_prompt': False, 'password_prompt': False, 'uid': None}

    def _read_until(self, predicate, deadline):
        while True:
            cleaned = _ANSI.sub(b'', self._buffer).replace(b'\r', b'')
            result = predicate(cleaned)
            if result is not None:
                return result
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Timed out waiting for the authenticated ADB shell')
            try:
                item = self._queue.get(timeout=min(remaining, 0.5))
            except queue.Empty:
                continue
            if item is None:
                raise ConnectionError('ADB shell closed or target disconnected; no automatic retry on another box')
            self._buffer += item
            if len(self._buffer) > 64 * 1024 * 1024:
                raise RuntimeError('ADB output exceeded the session limit')

    def _send(self, value):
        if self._process is None or self._process.poll() is not None:
            raise ConnectionError('ADB shell is no longer connected')
        self._process.stdin.write(value.encode('utf-8'))
        self._process.stdin.flush()

    def _secret(self):
        if self._password is None:
            if self._provider:
                self._password = self._provider()
            else:
                self._password = os.environ.get('QB560D_ADB_PASSWORD')
                if self._password is None:
                    self._password = getpass.getpass('Senha Linux da caixa para ' + self.user + ': ')
        if not isinstance(self._password, str) or not self._password or '\n' in self._password or '\r' in self._password:
            raise AuthenticationError('A nonempty, single-line Linux password is required')
        return self._password

    def redact(self, data):
        if self._password:
            return data.replace(self._password.encode('utf-8'), b'[REDACTED]')
        return data

    def connect(self, timeout=45):
        if self._process is not None:
            if self._process.poll() is not None:
                raise ConnectionError('ADB session ended; reconnect explicitly')
            return self
        self._queue = queue.Queue()
        self._buffer = b''
        self.auth.update({'login_prompt': False, 'password_prompt': False, 'uid': None})
        self._process = subprocess.Popen(self.base + ['shell'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, bufsize=0)
        process, chunks = self._process, self._queue
        def reader():
            try:
                while True:
                    data = process.stdout.read(4096)
                    if not data:
                        break
                    chunks.put(data)
            finally:
                chunks.put(None)
        threading.Thread(target=reader, daemon=True).start()
        deadline = time.monotonic() + timeout
        sent_user = False
        sent_password = False
        def state(data):
            if re.search(rb'(?i)login incorrect|authentication (?:failure|failed)|login failed', data):
                return 'failure'
            if re.search(rb'(?im)(?:^|\n)[^\n]{0,100}(?:login|username):\s*$', data):
                return 'login'
            if re.search(rb'(?i)password:\s*$', data):
                return 'password'
            if re.search(rb'(?:^|\n)[^\n]{0,160}[#$]\s*$', data):
                return 'shell'
            return None
        try:
            while True:
                event = self._read_until(state, deadline)
                self._buffer = b''
                if event == 'failure' or (event == 'login' and sent_password):
                    raise AuthenticationError('Linux login refused. Check username/password; no automatic retries were made.')
                if event == 'login':
                    if sent_user:
                        raise AuthenticationError('Repeated login prompt; authentication did not complete')
                    self.auth['login_prompt'] = True
                    sent_user = True
                    self._send(self.user + '\n')
                elif event == 'password':
                    if sent_password:
                        raise AuthenticationError('Repeated password prompt; refusing another attempt')
                    self.auth['password_prompt'] = True
                    sent_password = True
                    self._send(self._secret() + '\n')
                else:
                    break
            # Suppress command echo before framing output. Login itself manages password echo.
            token = '__QB_UID_' + uuid.uuid4().hex + '__'
            self._send("stty -echo; PS1=; PS2=; export PS1 PS2; printf '\\n" + token + "='; id -u\n")
            match = self._read_until(lambda data: re.search(re.escape(token.encode()) + rb'=(\d+)\n', data), deadline)
            self.auth['uid'] = int(match.group(1))
            self._buffer = b''
            if self.auth['uid'] != 0:
                raise AuthenticationError('Authenticated account is not root; uid=' + str(self.auth['uid']))
            return self
        except Exception:
            self.close()
            raise

    def run(self, command, timeout=90):
        self.connect()
        token = '__QB_CMD_' + uuid.uuid4().hex + '__'
        begin, end = (token + '_BEGIN').encode(), (token + '_END').encode()
        encoded = base64.encodebytes(command.encode('utf-8')).decode('ascii')
        delimiter = token + '_DATA'
        script = "printf '\\n%s\\n' '" + begin.decode() + "'\nbase64 -d <<'" + delimiter + "' | sh\n" + encoded + delimiter + "\nqb_rc=$?\nprintf '\\n%s=%s\\n' '" + end.decode() + "' \"$qb_rc\"\n"
        self._buffer = b''
        self._send(script)
        def complete(data):
            match = re.search(re.escape(end) + rb'=(\d+)\n', data)
            return (data, match) if match else None
        try:
            data, match = self._read_until(complete, time.monotonic() + timeout)
        except Exception:
            self.close()
            raise
        start = data.find(begin + b'\n')
        if start < 0:
            raise RuntimeError('Missing authenticated command start marker')
        output = data[start + len(begin) + 1:match.start()]
        self._buffer = b''
        return subprocess.CompletedProcess(self.base + ['shell', '<authenticated command>'], int(match.group(1)), self.redact(output), b'')

    def transfer(self, action, source, destination, **kwargs):
        self.connect()
        return transfer_files(self.base, action, source, destination, **kwargs)

    def close(self):
        process = self._process
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    self._send('exit\n')
                    process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired, ConnectionError):
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
        finally:
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()
            self._process = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *_):
        self.close()


def cached_session(base):
    key = tuple(base)
    if key not in _SESSIONS:
        _SESSIONS[key] = AdbSession(base=base)
    return _SESSIONS[key]


def run_shell(base, command, timeout=90):
    return cached_session(base).run(command, timeout)


def transfer(base, action, source, destination, **kwargs):
    return cached_session(base).transfer(action, source, destination, **kwargs)


@atexit.register
def close_sessions():
    for session in _SESSIONS.values():
        session.close()

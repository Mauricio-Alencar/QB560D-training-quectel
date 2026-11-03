"""Authenticated ADB shell, including firmware that starts a Linux login prompt."""
import base64,getpass,json,os,queue,re,shlex,subprocess,threading,time,uuid
from pathlib import Path
from adb_transport import local_path, resolve_adb, transfer_files

def select_device(executable,serial=None):
    executable=resolve_adb(executable)
    raw=subprocess.check_output([executable,'devices','-l'],text=True,timeout=15)
    devices=[r.split() for r in raw.splitlines()[1:] if len(r.split())>1 and r.split()[1]=='device']
    if serial:devices=[r for r in devices if r[0]==serial]
    if len(devices)!=1:raise RuntimeError('Expected exactly one authorized ADB device; use --serial if necessary.\n'+raw)
    row=devices[0];transport=next((x.split(':',1)[1] for x in row if x.startswith('transport_id:')),None)
    return [executable,'-t',transport] if transport else [executable,'-s',row[0]],' '.join(row),raw

class Session:
    def __init__(self,executable,serial=None,user='root',password=None):
        self.base,self.identity,self.devices=select_device(executable,serial)
        self.password=password;self.user=user;self.parts=queue.Queue();self.pending=b''
        self.proc=subprocess.Popen(self.base+['shell'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
        self.reader=threading.Thread(target=self._reader,daemon=True);self.reader.start()
        first=self._until(rb'(?:login:\s*$|[^\r\n]*[#$]\s*$)',20)
        if re.search(rb'login:\s*$',first):
            self._send(user+'\n');self._until(rb'Password:\s*$',10)
            if self.password is None:self.password=getpass.getpass('Target password (not saved): ')
            self._send(self.password+'\n')
            answer=self._until(rb'(?:login:\s*$|[^\r\n]*[#$]\s*$)',20)
            if re.search(rb'login:\s*$',answer) or b'Login incorrect' in answer:raise RuntimeError('Target login failed')
        token='__SESSION_READY_'+uuid.uuid4().hex+'__'
        self._send("stty -echo 2>/dev/null; export TERM=dumb LC_ALL=C; unset PROMPT_COMMAND; PS1=''; printf '\\n"+token+"\\n'\n")
        self._until(token.encode()+rb'\r*\n',10)
    def _reader(self):
        try:
            while True:
                data=os.read(self.proc.stdout.fileno(),65536)
                if not data:break
                self.parts.put(data)
        finally:self.parts.put(None)
    def _send(self,text):
        self.proc.stdin.write(text.encode('utf-8'));self.proc.stdin.flush()
    def _until(self,pattern,timeout):
        deadline=time.monotonic()+timeout;regex=re.compile(pattern,re.M)
        while True:
            match=regex.search(self.pending)
            if match:
                result=self.pending[:match.end()];self.pending=self.pending[match.end():];return result
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('ADB shell did not return the expected marker within '+str(timeout)+' seconds')
            try:part=self.parts.get(timeout=remaining)
            except queue.Empty:raise TimeoutError('ADB shell timed out')
            if part is None:raise RuntimeError('ADB shell disconnected')
            self.pending+=part
    def run(self,command,evidence,label,timeout=90,check=True):
        if not re.fullmatch(r'[A-Za-z0-9._-]+',label):raise ValueError('Invalid evidence label')
        token=uuid.uuid4().hex;begin='__BEGIN_'+token+'__';end='__END_'+token+'__='
        encoded=base64.b64encode(command.encode('utf-8')).decode()
        # Keep each terminal input line below Linux's canonical-input limit.
        self._send("provision_payload=''\n")
        for i in range(0,len(encoded),512):self._send('provision_payload=${provision_payload}'+encoded[i:i+512]+'\n')
        self._send("printf '\\n"+begin+"\\n'; provision_code=$(printf %s \"$provision_payload\" | base64 -d) && sh -e -c \"$provision_code\"; provision_rc=$?; unset provision_payload provision_code; printf '\\n"+end+"%s\\n' \"$provision_rc\"\n")
        raw=self._until(end.encode()+rb'\d+\r*\n',timeout)
        output=raw.decode('utf-8',errors='replace').replace('\r','')
        output=output.split(begin+'\n',1)[-1];status=int(re.search(re.escape(end)+r'(\d+)',output).group(1));output=output.split(end,1)[0].rstrip()+'\n'
        output=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',output)
        if self.password:output=output.replace(self.password,'[REDACTED]')
        evidence=local_path(evidence);evidence.mkdir(parents=True,exist_ok=True)
        (evidence/(label+'.log')).write_text(output,encoding='utf-8')
        (evidence/(label+'.json')).write_text(json.dumps(dict(command=command,exit_code=status),indent=2)+'\n',encoding='utf-8')
        print(label+': exit '+str(status),flush=True)
        if check and status:raise RuntimeError(label+' failed; see '+str(evidence/(label+'.log')))
        return output,status
    def python(self,code,evidence,label,timeout=120):
        encoded=base64.b64encode(code.encode('utf-8')).decode()
        return self.run("printf %s "+encoded+" | base64 -d | python3",evidence,label,timeout)[0]
    def push(self,source,destination):
        return transfer_files(self.base,'push',source,destination,check=True,timeout=180)
    def pull(self,source,destination):
        local_path(destination).mkdir(parents=True,exist_ok=True)
        return transfer_files(self.base,'pull',source,destination,check=True,timeout=180)
    def close(self):
        if self.proc.poll() is None:
            try:self._send('exit\n');self.proc.wait(timeout=3)
            except (OSError,subprocess.TimeoutExpired):self.proc.terminate()
        self.password=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

class RuntimeAdapter:
    """Methods expected by the existing isolated QAIRT staging/validation module."""
    def __init__(self,session):self.session=session;self.base=session.base;self.identity=session.identity
    def shell(self,command,evidence,name,timeout=150,allow_failure=False):return self.session.run(command,evidence,name,timeout,not allow_failure)
    def python(self,code,evidence,name):return self.session.python(code,evidence,name)
    def push(self,source,destination):return self.session.push(source,destination)
    def pull(self,source,destination):return self.session.pull(source,destination)

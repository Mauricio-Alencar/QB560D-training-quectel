"""Extract selected QAIRT SDK members with bounded HTTP ranges and ZIP CRC checks."""
import argparse, hashlib, io, json, os, re, urllib.request, zipfile, zlib
from pathlib import Path

class RemoteFile(io.RawIOBase):
    def __init__(self,url):
        self.url=url
        self.transferred=0
        req=urllib.request.Request(url,headers={"Range":"bytes=0-7","User-Agent":"QB560D-Isolated-Runtime-Test/1.0"})
        with urllib.request.urlopen(req,timeout=35) as r:
            if r.status!=206: raise ValueError("Server did not support bounded ranges")
            self.size=int(r.headers["Content-Range"].split("/")[-1])
            r.read(8)
        self.position=0
        self.cache=[]
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        return self.position
    def read(self,count=-1):
        count=self.size-self.position if count<0 else min(count,self.size-self.position)
        if count>128*1024*1024: raise ValueError("Refusing oversized read")
        if count<=0:return b""
        start=self.position
        self.position+=count
        for offset,data in self.cache:
            if offset<=start and start+count<=offset+len(data):return data[start-offset:start-offset+count]
        begin=(start//1048576)*1048576
        end=min(self.size,max(start+count,begin+1048576))
        req=urllib.request.Request(self.url,headers={"Range":f"bytes={begin}-{end-1}","User-Agent":"QB560D-Isolated-Runtime-Test/1.0"})
        with urllib.request.urlopen(req,timeout=60) as r:
            if r.status!=206:raise ValueError("Server ignored Range")
            if not r.headers.get("Content-Range","").startswith(f"bytes {begin}-{end-1}/"):raise ValueError("Unexpected Content-Range")
            data=r.read(end-begin+1)
        if len(data)!=end-begin:raise ValueError("Truncated or oversized range")
        self.transferred+=len(data)
        if len(data)<16*1048576:
            self.cache.append((begin,data))
            self.cache=self.cache[-40:]
        return data[start-begin:start-begin+count]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",required=True)
    p.add_argument("--dest",required=True)
    p.add_argument("--pattern",action="append",default=[])
    a=p.parse_args()
    dest=Path(a.dest).resolve()
    dest.mkdir(parents=True,exist_ok=True)
    remote=RemoteFile(a.url)
    receipts=[]
    with zipfile.ZipFile(remote) as z:
        entries=[dict(name=i.filename,bytes=i.file_size,compressed=i.compress_size) for i in z.infolist()]
        (dest/"sdk-index.json").write_text(json.dumps(entries,indent=2)+"\n",encoding="utf-8")
        for i in z.infolist():
            if i.is_dir() or not any(re.search(pattern,i.filename) for pattern in a.pattern): continue
            target=(dest/i.filename).resolve()
            if dest not in target.parents: raise ValueError("Unsafe ZIP member")
            if i.file_size>160*1048576:raise ValueError("Refusing oversized member")
            payload=target.read_bytes() if target.is_file() else b""
            if len(payload)!=i.file_size or zlib.crc32(payload)!=i.CRC:
                payload=z.read(i)
                if len(payload)!=i.file_size or zlib.crc32(payload)!=i.CRC:raise ValueError("ZIP CRC mismatch")
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(payload)
            row=dict(member=i.filename,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
            receipts.append(row)
            print(json.dumps(row),flush=True)
    (dest/"sdk-extraction-receipt.json").write_text(json.dumps(dict(url=a.url,archive_bytes=remote.size,transferred_bytes=remote.transferred,members=receipts),indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(index_entries=len(entries),selected=len(receipts),transferred_bytes=remote.transferred)),flush=True)
if __name__=="__main__":main()


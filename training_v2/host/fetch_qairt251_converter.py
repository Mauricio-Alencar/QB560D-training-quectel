"""Fetch a separate Windows/Python 3.12 conversion subset of the pinned public SDK."""
import argparse,hashlib,json,os,re,sys,zipfile,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT
sys.path.insert(0,str(REPO/'runtimes/qairt_2_51'))
from sdk_download import RemoteFile
URL='https://softwarecenter.qualcomm.com/api/download/software/sdks/Qualcomm_AI_Runtime_Community/All/2.51.40.260930/v2.51.40.260930.zip'
VERSION='2.51.40.260930'
def selected(name):
    return bool(re.search(r'/lib/python/.*\.py$',name) or re.search(r'/lib/python/.*/windows-x86_64/.*312\.pyd$',name) or re.search(r'/lib/x86_64-windows-msvc/(SNPE|QnnCpu|QnnSystem|QnnModelDlc|QnnIr)\.dll$',name) or re.search(r'/bin/x86_64-windows-msvc/(qairt-converter|qairt-quantizer|qairt-dlc-info|qairt-dlc-to-json|snpe-dlc-info|snpe-dlc-quant\.exe)$',name) or name.endswith('/LICENSE.pdf') or name.endswith('/bin/check-windows-dependency.ps1') or re.search(r'/docs/QAIRT-Docs/SNPE/general/(qairt_converter|qairt_quantizer|tflite.*|windows.*)\.html$',name))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dest',type=Path,default=ROOT/'.build/sdk251-host');a=p.parse_args();dest=a.dest.resolve();dest.mkdir(parents=True,exist_ok=True)
    records=[];remote=RemoteFile(URL)
    with zipfile.ZipFile(remote) as z:
        for info in z.infolist():
            if info.is_dir() or not selected(info.filename):continue
            target=(dest/info.filename).resolve();assert dest in target.parents
            io_path=Path('\\\\?\\'+str(target)) if os.name=='nt' else target
            blob=io_path.read_bytes() if io_path.is_file() else b''
            if len(blob)!=info.file_size or zlib.crc32(blob)!=info.CRC:
                blob=z.read(info);assert len(blob)==info.file_size and zlib.crc32(blob)==info.CRC
                io_path.parent.mkdir(parents=True,exist_ok=True);io_path.write_bytes(blob)
            records.append(dict(member=info.filename,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()))
            if len(records)%100==0:print('SDK files:',len(records),flush=True)
    (dest/'receipt.json').write_text(json.dumps(dict(version=VERSION,url=URL,archive_bytes=remote.size,transferred_bytes=remote.transferred,files=records),indent=2),encoding='utf-8')
    print('SDK_CONVERTER_READY:',len(records),'files;',remote.transferred,'bytes transferred',flush=True)
if __name__=='__main__':main()

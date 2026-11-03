"""Extract QNN profiles for an existing recorded validation run."""
import argparse,json
from pathlib import Path
from update_qairt import Adb,environment,require_owner
def collect(adb,remote,remote_output,evidence):
    env=environment(remote)
    for backend in ("cpu","htp"):
        folder=remote_output+"/"+backend
        adb.shell(env+" "+remote+"/bin/qnn-profile-viewer --input_log "+folder+"/qnn-profiling-data_0.log --output "+folder+"/profile.csv",evidence,"profile-"+backend,timeout=40)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--adb")
    p.add_argument('--serial')
    p.add_argument('--transport-id')
    a=p.parse_args()
    record=json.loads((a.evidence/"test-run.json").read_text(encoding="utf-8"))
    adb=Adb(a.adb,a.serial,a.transport_id);require_owner(adb,record["remote"],a.evidence)
    collect(adb,record["remote"],record["remote_output"],a.evidence)
    adb.pull(record["remote_output"],a.evidence/"target")
if __name__=="__main__":main()


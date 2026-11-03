"""Build the offline, target-only HTP controls from reviewed artifacts."""
import ast
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import tarfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    files = {}
    def add(name, source):
        if name.startswith('/') or '..' in Path(name).parts:
            raise ValueError('Unsafe bundle path')
        files[name] = Path(source).read_bytes()
    def store(name, value):
        files[name] = (json.dumps(value, indent=2)+'\n').encode('utf-8')
    htp = ROOT/'htp251'
    lock = json.loads((htp/'ARTIFACTS.lock.json').read_text(encoding='utf-8'))['files']
    def locked(name):
        path = htp/name
        assert sha(path.read_bytes()) == lock[name]['sha256'], name
        return path
    original = json.loads(locked('models.json').read_text(encoding='utf-8'))
    models = {}
    for task, spec in original['models'].items():
        key = 'models/'+task+'.dlc'
        add(key, locked(spec['dlc']))
        models[task] = {k: spec[k] for k in ('input_name','outputs','source_model','source_sha256')}
        models[task].update(dlc=key, dlc_sha256=spec['dlc_sha256'])
        if 'input_mode' in spec:
            models[task]['input_mode'] = spec['input_mode']
    store('assets/models.json', models)
    add('assets/source-contracts.json', locked('source-contracts.json'))
    add('assets/ssd_anchors.npy', locked('ssd_anchors.npy'))
    add('assets/profiles.json', ROOT/'ai/profiles.json')
    for name in ('imagenet_labels.txt','coco_labels.txt'):
        add('labels/'+name, ROOT/'models'/name)
    add('run.sh', ROOT/'htp251/target/run.sh')
    add('ai/htp_target.py', ROOT/'ai/htp_target.py')
    add('ai/run_demo.py', ROOT/'ai/run_demo.py')
    for path in sorted((ROOT/'media/controls').iterdir()):
        if path.is_file():
            add('media/controls/'+path.name, path)
    baseline = ROOT/'evidence/vision-controls/20261101-explicit-htp'
    summary = json.loads((baseline/'summary.json').read_text(encoding='utf-8'))
    assert summary['status'] == 'PASS_HTP_REFERENCE_CONTROLS'
    cases = json.loads((ROOT/'media/controls/cases.json').read_text(encoding='utf-8'))['cases']
    for spec in cases:
        folder = baseline/spec['id']
        refdir = folder/'reference'/spec['task']
        refs = list(refdir.glob('*.json'));assert len(refs) == 1
        reference = json.loads(refs[0].read_text(encoding='utf-8'))
        assert reference['model_sha256'] == models[spec['task']]['source_sha256']
        spec['prepared_tensor_sha256'] = sha((folder/'input.raw').read_bytes())
        spec['source_image_sha256'] = sha((ROOT/'media/controls'/spec['image']).read_bytes())
        store('references/'+spec['id']+'.json', reference)
        if spec['task'] == 'segmentation':
            arrays = list(refdir.glob('*.npz'));assert len(arrays) == 1
            with np.load(arrays[0], allow_pickle=False) as outputs:
                mask = np.argmax(outputs[sorted(outputs.files)[0]][0], axis=-1) == 15
            stream = io.BytesIO();np.savez_compressed(stream, person_mask=mask)
            files['references/'+spec['id']+'.npz'] = stream.getvalue()
    manifest = dict(package='qb560d-htp-controls-target-v1',
                    built_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                    runtime_version=original['runtime_version'], cases=cases,
                    cpu_reference='Saved original TFLite CPU outputs from 20261101-explicit-htp; not executed at runtime',
                    dependencies='Prepared target: Python3.8, NumPy and Pillow with Image.Resampling, isolated QAIRT2.51 ARM64/HTPv68',
                    files={name:sha(data) for name,data in sorted(files.items())})
    store('MANIFEST.json', manifest)
    for name,data in files.items():
        if name.endswith('.py'):
            ast.parse(data.decode('utf-8'), filename=name, feature_version=(3,8))
    out = ROOT/'offline/htp-controls-target.tar.gz';out.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(out,'w:gz',format=tarfile.PAX_FORMAT) as tar:
        for name,data in sorted(files.items()):
            info=tarfile.TarInfo('htp-controls/'+name);info.size=len(data);info.mtime=0
            info.mode=0o755 if name=='run.sh' else 0o644
            tar.addfile(info,io.BytesIO(data))
    digest=sha(out.read_bytes())
    out.with_name(out.name+'.sha256').write_text(digest+'  '+out.name+'\n',encoding='ascii')
    receipt=dict(package=manifest['package'],archive=out.relative_to(ROOT).as_posix(),sha256=digest,
                 bytes=out.stat().st_size,files=len(files),cases=len(cases),runtime_version=manifest['runtime_version'])
    out.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()

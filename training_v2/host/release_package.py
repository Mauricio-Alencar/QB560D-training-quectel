"""Build one complete, portable training ZIP from reviewed sources and locked inputs."""
import argparse,datetime as dt,hashlib,json,os,zipfile
from pathlib import Path
from validate_release import validate,validate_selection
from release_policy import GIT_EXCLUSIONS,release_exclusion_reason
TRAINING=Path(__file__).resolve().parents[1]
PROJECT=TRAINING.parent
REVISION='0.12.0-student-package'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def checked_input(path):
    path=Path(path).absolute()
    for candidate in (path,path.resolve()):
        if not candidate.is_relative_to(PROJECT):raise ValueError('External release input: '+str(path))
        reason=release_exclusion_reason(candidate.relative_to(PROJECT))
        if reason:raise ValueError('Forbidden release input: '+str(path)+'; '+reason)
    if not path.is_file():raise ValueError('Missing release input: '+str(path))
    return path.resolve()

def collect():
    files=set()
    def add(path):
        files.add(checked_input(path))
    def tree(relative):
        for parent,dirs,names in os.walk(TRAINING/relative):
            dirs[:]=[d for d in dirs if not release_exclusion_reason((Path(parent)/d).relative_to(PROJECT))]
            for name in names:
                path=Path(parent)/name
                if not release_exclusion_reason(path.relative_to(PROJECT)):add(path)
    for name in ('app','ai','config','docs','host','media','models','target','tests','wheelhouse','offline','vision_controls','Qualcomm_AI_Hub_Training'):tree(name)
    add(TRAINING/'README.md');add(TRAINING/'slides/QB560D_EU_Training.pptx')
    for path in read(TRAINING/'config/release-evidence.json')['files']:add(TRAINING/path)
    # Only explicitly prepared public summaries, never the raw network/RIL logs.
    for path in TRAINING.glob('evidence/reorganization-validation/*/release/*.json'):add(path)
    docker=TRAINING/'demos/docker'
    for name in ('app','config','host','target','offline','tests','evidence'):tree('demos/docker/'+name)
    for name in ('README.md','GUIA_ALUNO_OFFLINE.md','deploy-offline.ps1'):add(docker/name)
    add(TRAINING/'demos/README.md')
    tree('demos/hand_gesture/assets')
    for path in (TRAINING/'demos/hand_gesture').iterdir():
        if path.is_file() and path.suffix in {'.py','.md','.txt','.json'}:add(path)
    for name in ('fw-20261101','final-htp','final-seven-both','negative-dog'):tree('demos/hand_gesture/evidence/'+name)
    runtime=TRAINING/'runtimes/qairt_2_51'
    for path in runtime.iterdir():
        if path.is_file() and path.suffix in {'.py','.md','.me','.txt','.json'} and path.name!='package-manifest.json':add(path)
    tree('runtimes/qairt_2_51/assets')
    for row in read(runtime/'versions.lock.json')['files']:
        path=runtime/row['path']
        if sha(path)!=row['sha256']:raise ValueError('Locked QAIRT input changed: '+row['path'])
        add(path)
    for name in ('fw-20261101-v2','persistent-20261101/mobilenet','persistent-20261101/stage'):tree('runtimes/qairt_2_51/evidence/'+name)
    provision=TRAINING/'provision_target'
    for path in provision.iterdir():
        if path.is_file() and path.suffix in {'.py','.ps1','.txt','.json'} and not release_exclusion_reason(path.relative_to(PROJECT)):add(path)
    for row in read(provision/'sources.lock.json'):
        path=provision/'cache'/row['name']
        if sha(path)!=row['sha256']:raise ValueError('Locked provisioning input changed: '+row['name'])
        add(path)
    for name in ('README.md','platform-tools.lock.json','Quectel_ADB_driver_20180404.rar'):add(TRAINING/'tools'/name)
    for name,spec in read(TRAINING/'tools/platform-tools.lock.json')['files'].items():
        path=TRAINING/'tools/platform-tools'/name
        if sha(path)!=spec['sha256']:raise ValueError('Locked ADB changed: '+name)
        add(path)
    for path in (PROJECT/'references').iterdir():
        if path.is_file():add(path)
    for name in ('README.md','AGENTS.md','LICENSE','LICENSE-CONTENT','LICENSING.md'):add(PROJECT/name)
    for module,filename in [(docker,'MANIFEST.json'),(runtime,'package-manifest.json')]:
        output=module/filename;old=read(output) if output.exists() else {}
        old.update(revision=REVISION,path_base='module directory',distribution='Complete training archive; shared host/ and tools/ are included',files={p.relative_to(module).as_posix():sha(p) for p in sorted(files) if p.is_relative_to(module) and p!=output})
        output.write_text(json.dumps(old,indent=2)+'\n',encoding='utf-8');add(output)
    return files
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--skip-cli-validation',action='store_true');args=parser.parse_args()
    report=validate(not args.skip_cli_validation)
    files=collect();report['selected_links']=validate_selection(files|{TRAINING/'RELEASE.json'})
    deck=TRAINING/'slides/QB560D_EU_Training.pptx';deck_hash=sha(deck)
    manifest={'schema':2,'revision':REVISION,'at_host_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'package_root':'aibox_training','file_paths_relative_to':'package root',
        'entrypoint':'training_v2/README.md','host_working_directory':'training_v2',
        'slides':{'canonical_file':'slides/QB560D_EU_Training.pptx','count':report['slides'],'sha256_at_packaging':deck_hash,'path_base':'training_v2'},
        'modules':{'provisioning':'provision_target/README.txt','docker':'demos/docker/GUIA_ALUNO_OFFLINE.md','ai_hub':'Qualcomm_AI_Hub_Training/README.md','gestures':'demos/hand_gesture/README.md','qairt':'runtimes/qairt_2_51/README.md','htp':'htp251/README.md'},
        'adb':{'transport':'host/adb_transport.py','provisioning_api':'host/provision_session.py','windows_client':'tools/platform-tools/adb.exe','path_base':'training_v2'},
        'provisioning':{'offline_inputs_included':True,'fresh_inventory_and_plan_required':True,'saved_machine_inventory_or_plan_distributed':False},
        'yocto':'Conceptual slides only; no setup/build lab execution',
        'aihub_materials':{'pdf_directory':'Qualcomm_AI_Hub_Training/apresentacoes','pdf_count':report['ai_hub_pdfs'],'offline_demo':'Qualcomm_AI_Hub_Training/demo_offline','cloud_account_required_for_new_jobs':True},
        'validation':report,'excluded':list(GIT_EXCLUSIONS)+['**/.git/','**/.gitignore','*.part','unselected preparation caches'],
        'publication_exclusions':GIT_EXCLUSIONS,
        'licensing':{'copyright_holder':'José Maurício Alencar Filho','year':2026,'original_code':'MIT','original_teaching_material':'CC-BY-NC-SA-4.0','scope':'LICENSING.md','path_base':'package root','third_party':'Original licenses and redistribution terms retained'},
        'files':{p.relative_to(PROJECT).as_posix():sha(p) for p in sorted(files)}}
    release=TRAINING/'RELEASE.json';release.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');files.add(release)
    date=dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime('%Y%m%d')
    output=(args.output or PROJECT/'dist'/('QB560D_EU_Training_'+REVISION+'_'+date+'.zip')).resolve()
    if not output.is_relative_to(PROJECT/'dist'):raise ValueError('Release output must stay in dist/')
    if output.exists():raise FileExistsError('Use a new filename to preserve the existing release: '+str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in sorted(files):archive.write(p,'aibox_training/'+p.relative_to(PROJECT).as_posix())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise RuntimeError('ZIP integrity failed')
        for name,digest in manifest['files'].items():
            if hashlib.sha256(archive.read('aibox_training/'+name)).hexdigest()!=digest:raise RuntimeError('ZIP hash mismatch: '+name)
    if sha(deck)!=deck_hash:raise RuntimeError('Canonical deck changed during packaging; create a new release')
    output.with_suffix('.zip.sha256').write_text(sha(output)+'  '+output.name+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(output),'bytes':output.stat().st_size,'files':len(files),'revision':REVISION,'slides':report['slides'],'sha256':sha(output)},indent=2))
if __name__=='__main__':main()

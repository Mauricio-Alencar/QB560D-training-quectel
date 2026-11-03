"""Validate portable training paths and pinned assets without connecting to a box."""
import argparse,ast,hashlib,json,os,re,subprocess,sys,urllib.parse,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
from pptx_integrity import notes_master_problems
from release_policy import release_exclusion_reason

TRAINING=Path(__file__).resolve().parents[1]
PACKAGE=TRAINING.parent
SKIP={'.build','.venv','__pycache__','cache','evidence','assets','models','fontes','platform-tools'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def active_files():
    for parent,dirs,files in os.walk(TRAINING):
        dirs[:]=[d for d in dirs if d not in SKIP and not release_exclusion_reason((Path(parent)/d).relative_to(PACKAGE))]
        for name in files:
            path=Path(parent)/name
            if not release_exclusion_reason(path.relative_to(PACKAGE)):yield path
    for name in ('README.md','LICENSING.md'):yield PACKAGE/name

def validate_selection(files,package_root=None):
    """Check local links against the actual release, not the preparation tree."""
    root=Path(package_root or PACKAGE).resolve()
    selected={Path(path).resolve() for path in files}
    directories={parent for path in selected for parent in path.parents if parent.is_relative_to(root)}
    problems=[];documents=0;hyperlinks=0
    def check(source,target):
        target=target.strip().strip('<>')
        if re.match(r'^(?:https?://|mailto:|#)',target,re.I):return
        target=urllib.parse.unquote(target.split('#')[0])
        if target:
            destination=(source.parent/target).resolve()
            if destination not in selected and destination not in directories:
                problems.append(str(source.relative_to(root))+': link not in student package '+target)
    for path in sorted(selected):
        if path.suffix in {'.md','.me'}:
            documents+=1
            for match in re.finditer(r'\]\(([^\n)]+)\)',path.read_text(encoding='utf-8-sig')):check(path,match[1])
        elif path.name=='QB560D_EU_Training.pptx':
            with zipfile.ZipFile(path) as archive:
                for part in archive.namelist():
                    if not part.endswith('.rels'):continue
                    for relation in E.fromstring(archive.read(part)):
                        if relation.get('TargetMode')=='External' and relation.get('Type','').endswith('/hyperlink'):
                            hyperlinks+=1;check(path,relation.get('Target',''))
    if problems:raise RuntimeError('\n'.join(problems))
    return {'result':'PASS_SELECTED_LINKS','documents':documents,'pptx_hyperlinks':hyperlinks}

def validate(cli=True):
    sys.path.insert(0,str(TRAINING/'runtimes/qairt_2_51'))
    sys.path.insert(0,str(TRAINING/'demos/hand_gesture'))
    problems=[];checked=0
    for p in active_files():
        if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8-sig'));checked+=1
        if p.suffix in {'.md','.me'}:
            text=p.read_text(encoding='utf-8-sig')
            for m in re.finditer(r'\]\(([^\n)]+)\)',text):
                target=m[1].strip().strip('<>')
                if re.match(r'^(?:https?://|mailto:|#)',target,re.I):continue
                target=urllib.parse.unquote(target.split('#')[0])
                if target:
                    destination=(p.parent/target).resolve()
                    if not destination.exists():problems.append(str(p.relative_to(PACKAGE))+': missing link '+target)
                    elif destination.is_relative_to(PACKAGE) and release_exclusion_reason(destination.relative_to(PACKAGE)):
                        problems.append(str(p.relative_to(PACKAGE))+': link to excluded material '+target)
    count=0
    deck=TRAINING/'slides/QB560D_EU_Training.pptx'
    with zipfile.ZipFile(deck) as z:
        problems.extend(notes_master_problems(z))
        count=len(E.fromstring(z.read('ppt/presentation.xml')).find('{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst'))
        for part in z.namelist():
            if not part.endswith('.rels'):continue
            for rel in E.fromstring(z.read(part)):
                target=urllib.parse.unquote(rel.get('Target',''))
                if rel.get('TargetMode')=='External' and rel.get('Type','').endswith('/hyperlink'):
                    if re.match(r'^(?:file:|[A-Za-z]:)',target):problems.append('PPTX absolute local hyperlink: '+target)
                    elif not re.match(r'^https?://',target):
                        destination=(deck.parent/target).resolve()
                        if not destination.exists():problems.append('PPTX missing hyperlink: '+target)
                        elif destination.is_relative_to(PACKAGE) and release_exclusion_reason(destination.relative_to(PACKAGE)):
                            problems.append('PPTX hyperlink to excluded material: '+target)
    platform=json.loads((TRAINING/'tools/platform-tools.lock.json').read_text())
    for name,spec in platform['files'].items():
        if sha(TRAINING/'tools/platform-tools'/name)!=spec['sha256']:problems.append('ADB lock mismatch: '+name)
    import update_qairt
    update_qairt.check_lock()
    import gesture_demo
    gesture_demo.check_assets()
    materials=json.loads((TRAINING/'Qualcomm_AI_Hub_Training/materiais.lock.json').read_text(encoding='utf-8-sig'))
    for spec in materials['materials']:
        p=TRAINING/'Qualcomm_AI_Hub_Training'/spec['file']
        if sha(p)!=spec['sha256']:problems.append('AI Hub PDF lock mismatch: '+spec['file'])
    commands=[['host/adb_lab.py','--help'],['provision_target/provision.py','--help'],['host/htp251_workshop.py','--help'],['host/deploy_htp_target.py','--help'],['host/validate_vision_controls.py','--help'],['demos/docker/host/deploy_offline.py','--help'],['demos/hand_gesture/gesture_demo.py','--help'],['runtimes/qairt_2_51/update_qairt.py','--help'],['Qualcomm_AI_Hub_Training/host/account.py','--help']]
    if cli:
        for command in commands:
            result=subprocess.run([sys.executable,'-B',str(TRAINING/command[0]),*command[1:]],cwd=PACKAGE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            if result.returncode:problems.append('CLI failed: '+command[0]+'\n'+result.stdout[-1800:])
    if problems:raise RuntimeError('\n'.join(problems))
    return {'result':'PASS_PORTABLE_TRAINING','python_files':checked,'slides':count,'ai_hub_pdfs':len(materials['materials']),'cli_entrypoints':len(commands) if cli else 0,'adb_transport':'host/adb_transport.py','hardware_connection_used':False}

if __name__=='__main__':
    sys.path.insert(0,str(TRAINING/'runtimes/qairt_2_51'));sys.path.insert(0,str(TRAINING/'demos/hand_gesture'))
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--no-cli',action='store_true');args=parser.parse_args()
    print(json.dumps(validate(not args.no_cli),indent=2))

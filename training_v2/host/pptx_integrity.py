"""Portable checks for the notes-master incompatibility that triggers Office repair."""
import argparse
import json
import posixpath
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as E

P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NOTES_MASTER_TYPE='application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml'


def resolve(part, target):
    return posixpath.normpath(target if target.startswith('/') else posixpath.join(posixpath.dirname(part), target)).lstrip('/')


def notes_master_problems(archive):
    problems=[]
    presentation=E.fromstring(archive.read('ppt/presentation.xml'))
    relationships=list(E.fromstring(archive.read('ppt/_rels/presentation.xml.rels')))
    master_rels=[r for r in relationships if r.get('Type','').endswith('/notesMaster')]
    master_list=presentation.find('{'+P+'}notesMasterIdLst')
    master_ids=list(master_list) if master_list is not None else []
    declared_parts=[e.get('PartName','').lstrip('/') for e in E.fromstring(archive.read('[Content_Types].xml')) if e.get('ContentType')==NOTES_MASTER_TYPE]
    if len(master_ids)>1:
        problems.append('PPTX notesMasterIdLst permits one notes master; found '+str(len(master_ids)))
    if len(master_rels)>1:
        problems.append('PPTX presentation permits one notesMaster relationship; found '+str(len(master_rels)))
    if len(declared_parts)>1:
        problems.append('PPTX contains multiple notes-master parts: '+str(len(declared_parts)))
    rel_ids={r.get('Id') for r in master_rels}
    if len(master_ids)!=len(master_rels) or any(e.get('{'+R+'}id') not in rel_ids for e in master_ids):
        problems.append('PPTX notes-master list and presentation relationships differ')
    canonical=resolve('ppt/presentation.xml',master_rels[0].get('Target','')) if len(master_rels)==1 else None
    if canonical and (canonical not in archive.namelist() or canonical not in declared_parts):
        problems.append('PPTX canonical notes-master part is missing or has an invalid content type')
    for part in archive.namelist():
        if not part.startswith('ppt/notesSlides/') or not part.endswith('.xml') or '/_rels/' in part:
            continue
        relpart=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
        if relpart not in archive.namelist():
            problems.append('PPTX notes slide is missing relationships: '+part)
            continue
        targets=[resolve(part,r.get('Target','')) for r in E.fromstring(archive.read(relpart)) if r.get('Type','').endswith('/notesMaster')]
        if len(targets)!=1 or canonical is None or targets[0]!=canonical:
            problems.append('PPTX notes slide does not use the single canonical notes master: '+part)
    return problems


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('presentation',type=Path)
    args=parser.parse_args()
    with zipfile.ZipFile(args.presentation) as archive:
        problems=notes_master_problems(archive)
    print(json.dumps({'result':'FAIL_PPTX_NOTES_MASTER' if problems else 'PASS_PPTX_NOTES_MASTER','problems':problems},indent=2))
    return 1 if problems else 0


if __name__=='__main__':
    sys.exit(main())

"""Publish a portable gallery of reviewed controls without large tensor dumps."""
from pathlib import Path
import html,json,shutil

ROOT=Path(__file__).resolve().parents[1]
def main():
    folders=[ROOT/'evidence/vision-controls/20261101-reference-controls',ROOT/'evidence/vision-controls/20261101-standing-controls']
    dest=ROOT/'vision_controls';dest.mkdir(exist_ok=True);rows=[];cards=[]
    for folder in folders:
        summary=json.loads((folder/'summary.json').read_text())
        assert summary['status']=='PASS_REFERENCE_CONTROLS'
        integrity=json.loads((folder/'runtime-integrity.json').read_text());assert integrity['passed']
        for row in summary['records']:
            spec=row['case'];case=folder/spec['id'];out=dest/spec['id'];out.mkdir(exist_ok=True)
            task=spec['task'];cpu=next((case/'reference'/task).glob('*.png'));gpu=next((case/'gpu/gpu'/task).glob('*.png'));htp=case/'htp/prediction.png'
            for label,path in [('input',case/'input.png'),('cpu',cpu),('gpu',gpu),('htp',htp)]:shutil.copyfile(path,out/(label+'.png'))
            # Paths in the public JSON are portable relative paths.
            public=dict(case=spec,passed=row['passed'],image_sha256=row['image_sha256'],cpu=row['cpu'],gpu=row['gpu'],htp=row['htp']['results'][0],raw_evidence_from_training_root=folder.relative_to(ROOT).as_posix(),runtime_integrity=integrity)
            (out/'result.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8');rows.append(public)
            title=html.escape(spec['id']);images=''.join('<figure><a href="'+spec['id']+'/'+b+'.png"><img src="'+spec['id']+'/'+b+'.png" alt="'+b+'"></a><figcaption>'+b.upper()+'</figcaption></figure>' for b in ['input','cpu','gpu','htp'])
            note='Yoga: use para discutir limites da pose/segmentação; para a demonstração principal, prefira a pessoa em pé.' if spec['id'] in ['full-body-pose','person-segmentation'] else ('Oclusão sintética identificada; pontos inferidos atrás do bloco não são ground truth.' if spec['id']=='occluded-pose' else '')
            if spec['id']=='no-person-detection':note='Controle de ausência de pessoa aprovado. O gato foi rotulado dog nos três backends: erro de classe documentado; não é aceitação da classe do animal.'
            cards.append('<section><h2>'+title+' — PASS funcional</h2><p>'+html.escape(note)+'</p><div>'+images+'</div><p><a href="'+spec['id']+'/result.json">JSON real CPU/GPU/HTP</a></p></section>')
    report=dict(status='PASS_11_REFERENCE_CONTROLS_WITH_VISUAL_LIMITS',cases=len(rows),backend_case_combinations=3*len(rows),scope='Selected public reference controls; no dataset accuracy or complete camera pipeline claim. CNN executes on target; HTP pre/postprocessing on host.',records=rows)
    (dest/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    page='<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>QB560D — controles de visão</title><style>body{font:16px Arial;margin:30px;color:#222}section{border-top:1px solid #aaa;margin-top:24px}section div{display:flex;gap:12px}figure{margin:0;width:24%}img{width:100%;height:300px;object-fit:contain;background:#eee}figcaption{text-align:center;padding:8px}a{color:#210079}</style><h1>Controles de visão — QB560D-EU</h1><p>11 casos, CPU TFLite 2.8.4, GPU OpenCL e HTP QAIRT/QNN 2.51. Clique para ampliar. Aprovação funcional nas amostras; limites visuais permanecem descritos no guia.</p><p><a href="../docs/VISION_CONTROLS.md">Guia, fontes, reprodução e limites</a></p>'+''.join(cards)+'</html>'
    (dest/'index.html').write_text(page,encoding='utf-8');print(report['status'],len(rows))
if __name__=='__main__':main()

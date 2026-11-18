"""Minimal existence, source-identity and saved-state dimension checks. No mj_step."""
import pathlib,json,csv,sqlite3,xml.etree.ElementTree as ET
ROOT=pathlib.Path('D:/softrobot-agent/runs/multitask-paper-data-20261118')
def first_json_item(p):
 with p.open(encoding='utf8') as f:
  s=f.read(262144).lstrip()
  if s.startswith('['):return json.JSONDecoder().raw_decode(s[1:].lstrip())[0]
  return None
for tid in ['T01','T02','T03','T04','T05','T06','T08','T09']:
 d=ROOT/tid;b=json.loads((d/'evidence_bundle.json').read_text(encoding='utf8'));checks=[]
 for fc in b['final_conditions']:
  c=sqlite3.connect('file:'+fc['store'].replace('\\','/')+'?mode=ro',uri=True)
  record={'condition':fc['condition'],'candidate_id':fc['candidate_id'],'run_id':fc['run_id'],'references':{},'models':[]}
  for key in ['candidate_reference','configuration_reference','result_reference','raw_reference']:
   aid=fc[key].split('#artifacts/')[-1]
   rr=c.execute('select length(body) from artifacts where id=?',(aid,)).fetchone()
   record['references'][key]={'exists':rr is not None,'bytes':rr[0] if rr else None}
  c.close()
  for xml in fc['original_xml_files']:
   p=pathlib.Path(xml);model={'xml':xml,'exists':p.exists()}
   if p.exists():
    root=ET.parse(p).getroot();joints=root.findall('.//worldbody//joint')
    widths={'free':7,'ball':4,'slide':1,'hinge':1}
    model['nq_from_original_scalar_joint_definitions']=sum(widths[j.get('type','hinge')] for j in joints)+7*len(root.findall('.//worldbody//freejoint'))
    assoc=[s for s in fc['recorded_state_sources'] if s.get('original_model_xml',str(pathlib.Path(s['path']).parent/'robot.xml'))==xml]
    states=[]
    for ss in assoc:
     if ss.get('role')=='robot_only_overview_do_not_load_as_full_scene':continue
     sp=pathlib.Path(ss['path']);v={'path':str(sp),'exists':sp.exists()}
     if sp.exists() and ss.get('format')=='csv':
      with sp.open(encoding='utf8') as f:r=next(csv.DictReader(f));qs=[float(r[k]) for k in ss['qpos_fields']]
      v['first_recorded_time_s']=float(r['time_s']);v['qpos_dimension']=len(qs)
     elif sp.exists() and sp.name=='samples.json':
      first=first_json_item(sp);v['qpos_dimension']=len(first.get('qpos_rad',[])) if first else None;v['first_recorded_time_s']=first.get('time_s') if first else None
     elif sp.exists() and ss.get('pointer')=='/task_evidence/arrays':
      original=json.loads(sp.read_text(encoding='utf8'));arrays=original['task_evidence']['arrays'];v['qpos_dimension']=len(arrays['qpos'][0]);v['first_recorded_time_s']=arrays['time_s'][0];v['saved_dense_states']=len(arrays['time_s']);v['original_joint_layout_last']=original['task_evidence']['joint_layout'][-1];v['source_pointer']='/task_evidence/arrays';v['robot_only_overview_note']='samples.json has only48 arm coordinates; complete dense qpos includes button_slide at address48'
     else:continue
     v['dimension_matches_model']=v['qpos_dimension']==model['nq_from_original_scalar_joint_definitions'];states.append(v)
    model['saved_state_checks']=states
   record['models'].append(model)
  checks.append(record)
 report={'task_id':tid,'scope':'original references exist and saved-state qpos dimensions match scalar original XML joints; no dynamic integration or exhaustive hash audit','checks':checks,'all_checked_references_exist':all(v['exists'] for r in checks for v in r['references'].values()),'all_checked_models_exist':all(v['exists'] for r in checks for v in r['models']),'all_checked_state_dimensions_match':all(v['dimension_matches_model'] for r in checks for m in r['models'] for v in m.get('saved_state_checks',[]))}
 (d/'lightweight_evidence_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(tid,report['all_checked_references_exist'],report['all_checked_models_exist'],report['all_checked_state_dimensions_match'])

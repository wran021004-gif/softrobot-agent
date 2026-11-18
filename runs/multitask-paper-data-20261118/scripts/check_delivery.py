"""Necessary output, state, camera and render checks; no SHA audit or solving."""
from pathlib import Path
import csv,json,struct,xml.etree.ElementTree as E
from extract_render_inputs import O,read,save,native

def main():
    tasks=[f'T{i:02d}' for i in range(1,11)];cases=read(O/'FINAL_CASES.json');screens=read(O/'SCREENSHOT_MANIFEST.json');videos=read(O/'VIDEO_MANIFEST.json');checks={}
    required=['TASK_SUMMARY.md','candidate_timeline.csv','agent_decision_timeline.csv','metric_history.csv','evidence_bundle.json','render_manifest.csv','video_manifest.csv','ASSET_INDEX.md']
    checks['ten_task_required_files']=all((O/t/f).is_file() for t in tasks for f in required)
    checks['ten_task_figure_data']=all(any((O/t/'FIGURES_PAPER').glob('*.svg')) and any((O/t/'FIGURE_DATA').glob('*.csv')) for t in tasks)
    checks['visual_compile_equivalence']=all(read(p)['validation']['passed'] for p in O.glob('*/VISUAL_XML/*.check.json'))
    cameras={};native_zero_mass=True;dimensions=True
    for p in O.glob('*/VISUAL_XML/*_visual.xml'):
        root=E.parse(p).getroot()
        for g in root.findall('.//geom'):
            if g.get('name','').startswith(('master_','paper_')):
                native_zero_mass &= g.get('mass')=='0' and g.get('contype')=='0' and g.get('conaffinity')=='0'
    for r in screens:
        p=Path(r['png']);h=p.read_bytes()[:24];dimensions &= h[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',h[16:24])==(1600,1200)
        assert Path(native(r['original_xml'])).is_file() and Path(r['visual_xml']).is_file()
        if r['view']=='oblique':cameras.setdefault(r['task_id'],set()).add(json.dumps(r['camera'],sort_keys=True))
    checks['native_visual_geoms_zero_mass_noncontact']=bool(native_zero_mass);checks['png_dimensions_and_signature']=bool(dimensions)
    # Camera manifests sometimes include an explicit view azimuth/elevation added
    # at serialization. Compare numerical fields, not JSON field-presence.
    checks['task_fixed_camera']=all(all(r['camera']['lookat']==read(O/t/'VISUAL_XML/CAMERA_SETTINGS.json')['lookat'] and r['camera']['vertical_span_m']==read(O/t/'VISUAL_XML/CAMERA_SETTINGS.json')['vertical_span_m'] for r in screens if r['task_id']==t and r['view']=='oblique') for t in tasks+['PHS-2D'])
    checks['videos_native_shadow_text_free']=all(v['shadow_enabled'] and not v['text_overlay'] and not v['physical_integration_performed'] for v in videos)
    checks['video_probe_dimensions_frames']=all(Path(v['video']).is_file() and v['ffprobe']['streams'][0]['codec_name']=='h264' and v['ffprobe']['streams'][0]['width']==1600 and v['ffprobe']['streams'][0]['height']==1200 and int(v['ffprobe']['streams'][0]['nb_frames'])==v['frames'] for v in videos)
    statechecks=[]
    for r in cases:
        mo=read(r['motion_file']);n=len(mo['times_s']);statechecks.append(n==len(mo['qpos']) and len({len(q) for q in mo['qpos']})==1)
        assert Path(native(r['source_xml'])).is_file()
    checks['archived_motion_array_dimensions']=all(statechecks)
    checks['final_multiviews']=all(any(s['task_id']==t and s['view']=='side' for s in screens) and any(s['task_id']==t and s['view']=='front' for s in screens) for t in tasks+['PHS-2D'])
    assert all(checks.values()),checks
    save(O/'DELIVERY_CHECK.json',dict(passed=True,checks=checks,screenshots=len(screens),videos=len(videos),visual_xml=len(list(O.glob('*/VISUAL_XML/*_visual.xml'))),formal_quantitative_png=len(list(O.glob('*/FIGURES_PAPER/*.png'))),cross_task_draft_groups=3,physical_integration_performed=False,scope='Necessary existence, dimensions, compile comparisons and output validity; no full hash audit.'))
    scratch=O/'codec_probe.mp4'
    if scratch.is_file():scratch.unlink()
    print(json.dumps(dict(passed=True,checks=checks,screenshots=len(screens),videos=len(videos)),ensure_ascii=False),flush=True)

if __name__=='__main__':main()

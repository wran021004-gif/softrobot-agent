"""Launch MATLAB's own saved-trajectory Figure; Python does not draw geometry."""
from pathlib import Path
from tools.artifact_tools import file_hash
from tools.state_io import read, atomic_json


def capture_tdcr(engine, source, output, indices, fps):
    """Model adapter for matlab_tdcr_planar_dynamic_v1; closes its own Figure."""
    import matlab
    import xml.etree.ElementTree as ET
    source = Path(source)
    ir = read(source/'robot_ir.json')
    if ir.get('robot_family') != 'tendon_driven_continuum':
        raise ValueError('UNSUPPORTED_MODEL: expected saved TDCR robot geometry')
    scene = ET.parse(source/'robot.xml').getroot().find('worldbody')
    # This planar adapter supports the saved floor/target scene only. Never hide
    # an unimplemented obstacle or use this drawing for a different model.
    if scene is None or any(g.get('name')!='floor' or g.get('type')!='plane' for g in scene.findall('geom')):
        raise ValueError('UNSUPPORTED_SCENE: TDCR Figure adapter supports a plane floor and target')
    if any(b.get('name')!='segment_0' for b in scene.findall('body')):
        raise ValueError('UNSUPPORTED_SCENE: additional bodies require a drawing adapter')
    return engine.tdcr_replay_saved(str(source), str(output), float(fps),
                                   matlab.double([[i+1 for i in indices]]), False, nargout=1)


def show_matlab(source, output=None):
    import matlab.engine
    source = Path(source).resolve()
    if read(source/'result.json')['backend'] != 'matlab':
        raise ValueError('MATLAB replay requires the MATLAB backend trajectory')
    output = Path(output).resolve() if output else None
    if output and any((output/name).exists() for name in ('native_scene.gif','native_scene.png','native_replay.json')):
        raise ValueError('EXPORT_EXISTS: use a new output folder')
    # A desktop session plus a blocking wait keeps the Figure visible and usable.
    # The normal numerical Engine helper intentionally does not request a desktop.
    eng = matlab.engine.start_matlab('-desktop')
    try:
        eng.addpath(str(Path(__file__).resolve().parents[1]/'matlab'), nargout=0)
        info = eng.tdcr_replay_saved(str(source), str(output) if output else '', 25., nargout=1)
        if output:
            manifest = read(output/'native_replay.json')
            manifest['source_hashes'] = {name:file_hash(source/name) for name in
                                       ('trajectory.json.gz','shared_input.json','robot_ir.json','result.json')}
            atomic_json(output/'native_replay.json',manifest)
            print('MATLAB Figure capture:', output/'native_scene.gif', flush=True)
        print('MATLAB Figure is open. Play/Pause, time slider and MATLAB camera tools are available.', flush=True)
        print('Saved diagnosis:', source/'diagnosis.json', flush=True)
        print('Close the Figure to exit this replay session. No integration or scoring.', flush=True)
        eng.eval("figure(findobj('Type','figure','Tag','Round9SavedReplay')); drawnow; waitfor(findobj('Type','figure','Tag','Round9SavedReplay'));",nargout=0)
    finally:
        eng.quit()

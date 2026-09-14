"""On-demand native video from registered saved results; no campaign/task constants."""
import bisect
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

from schemas.dynamic_workbench import RenderVideo
from tools.artifact_tools import file_hash
from tools.state_io import atomic_json, digest, read
from tools.trajectory_diagnosis import load_rows

CODE_ROOT = Path(__file__).resolve().parents[1]
MATLAB_ADAPTERS = {'matlab_tdcr_planar_dynamic_v1': 'tdcr_planar_saved_v1'}


def _source(root, registry, ref, backend):
    path = (root/ref).resolve()
    if not path.is_relative_to(root) or ref not in registry:
        raise ValueError('UNREGISTERED_RESULT: use an evidence result_ref from the run')
    if not path.is_file() or file_hash(path) != registry[ref]['sha256']:
        raise ValueError('RESULT_CHANGED_OR_MISSING: '+ref)
    result = read(path)
    if result.get('backend') != backend:
        raise ValueError('BACKEND_MISMATCH')
    folder = path.parent
    trajectory = (folder/result.get('trajectory_ref', 'trajectory.json.gz')).resolve()
    if not trajectory.is_relative_to(folder):
        raise ValueError('UNSUPPORTED_SOURCE: trajectory must be local to the saved result')
    required = [path, trajectory, folder/'robot.xml']
    if backend == 'matlab':
        required += [folder/'shared_input.json', folder/'robot_ir.json']
    missing = [p.name for p in required if not p.is_file()]
    if missing:
        raise ValueError('MISSING_SAVED_DATA: '+', '.join(missing))
    # Hash only source dependencies, never a containing run's state or derived
    # output. A result stored at the run root must cache just like a nested result.
    dependencies = set(required)
    dependencies.update(folder/name for name in ('shared_input.json','robot_ir.json') if (folder/name).is_file())
    pending = [folder/'robot.xml']; visited = set()
    while pending:
        xml = pending.pop()
        if xml in visited:continue
        visited.add(xml)
        tree = ET.parse(xml)
        compiler = tree.find('compiler')
        for node in tree.iter():
            if not node.get('file'):
                continue
            prefix = '' if compiler is None or node.tag not in ('mesh','texture') else compiler.get(
                'meshdir' if node.tag=='mesh' else 'texturedir', compiler.get('assetdir',''))
            asset = (xml.parent/prefix/node.get('file')).resolve()
            if not asset.is_relative_to(folder) or not asset.is_file():
                raise ValueError('MISSING_OR_EXTERNAL_SCENE_ASSET: '+node.get('file'))
            dependencies.add(asset)
            if node.tag=='include':pending.append(asset)
    hashes = {}
    for p in sorted(dependencies):
        if p.is_file():
            if not p.resolve().is_relative_to(folder):
                raise ValueError('EXTERNAL_SCENE_ASSET')
            h = file_hash(p); rel = p.relative_to(root).as_posix()
            if rel in registry and h != registry[rel]['sha256']:
                raise ValueError('SOURCE_CHANGED: '+rel)
            hashes[rel] = h
    return folder, result, trajectory, hashes


def _schedule(rows, start, end, fps):
    times = [float(r['time_s']) for r in rows]
    if not times or any(not math.isfinite(t) for t in times) or any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError('MISSING_OR_INVALID_SAVED_TIMESTAMPS')
    start = times[0] if start is None else max(start, times[0])
    end = times[-1] if end is None else min(end, times[-1])
    if end < start:
        raise ValueError('EMPTY_OR_REVERSED_TIME_INTERVAL')
    first = bisect.bisect_left(times, start-1e-10)
    if first == len(times) or times[first] > end+1e-10:
        raise ValueError('NO_SAVED_SAMPLE_IN_INTERVAL')
    start = times[first]
    scheduled = [start+i/fps for i in range(math.floor((end-start)*fps+1e-9)+1)]
    indices = [max(first,bisect.bisect_right(times,t+1e-10)-1) for t in scheduled]
    return times, scheduled, indices


def _mujoco_frames(folder, rows, indices, frames):
    import mujoco
    from PIL import Image
    from tools.native_replay import NativeReplay
    samples = [dict(time_s=r['time_s'], state=r.get('qpos_rad',r.get('qpos'))) for r in rows]
    player = NativeReplay(folder, observation=dict(backend='mujoco',samples=samples))
    player.model.vis.global_.offwidth = max(800,player.model.vis.global_.offwidth)
    player.model.vis.global_.offheight = max(600,player.model.vis.global_.offheight)
    with mujoco.Renderer(player.model,height=600,width=800) as renderer:
        for k,index in enumerate(indices):
            player.seek(player.times[index])
            renderer.update_scene(player.data,player.camera,player.option)
            Image.fromarray(renderer.render()).save(frames/f'frame_{k:06d}.png')


def _encode(frames, video, fps, engine, ffmpeg):
    if ffmpeg:
        subprocess.run([ffmpeg,'-v','error','-n','-framerate',str(fps),'-i',str(frames/'frame_%06d.png'),
                        '-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],
                       check=True, capture_output=True)
        # Decode once to reject truncated/unplayable output, not just its extension.
        subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True)
        return dict(encoder='FFmpeg libx264 / yuv420p',decode_verified=True)
    return dict(engine.encode_saved_frames(str(frames),str(video),float(fps),nargout=1))


def valid_video_manifest(root, manifest):
    """Read-only cache/workbench check: source and derived bytes must still match."""
    try:
        info = read(manifest)
        for ref,h in {**info['source_hashes'],**info['artifact_hashes']}.items():
            p = (root/ref).resolve()
            if not p.is_relative_to(root) or not p.is_file() or file_hash(p)!=h:
                return None
        return info
    except (OSError, ValueError, KeyError):
        return None


def render_simulation_video(root, evidence_registry, result_ref, backend,
                            t_start_s=None, t_end_s=None, fps=25):
    """Shared dispatch/CLI implementation. Mutates only derived files and registry."""
    started = time.monotonic(); root = Path(root).resolve()
    params = RenderVideo(result_ref=result_ref,backend=backend,t_start_s=t_start_s,t_end_s=t_end_s,fps=fps).model_dump()
    folder,result,trajectory,hashes = _source(root,evidence_registry,result_ref,backend)
    model_id = result.get('render_adapter',result.get('model_id'))
    adapter = 'mujoco_saved_qpos_v1' if backend=='mujoco' else MATLAB_ADAPTERS.get(model_id)
    if adapter is None:
        raise ValueError('UNSUPPORTED_RENDER_ADAPTER: '+str(model_id))
    code = ['tools/simulation_video.py','tools/native_replay.py','tools/matlab_replay.py',
            'matlab/tdcr_replay_saved.m','matlab/encode_saved_frames.m']
    identity = dict(parameters=params,source_hashes=hashes,adapter=adapter,
                    renderer_sources={p:file_hash(CODE_ROOT/p) for p in code})
    output = root/'observations/videos'/digest(identity)[:20]
    manifest = output/'native_video.json'
    # Adapter IDs version the drawing semantics; unrelated implementation edits
    # must not discard a valid recording of the same sources and parameters.
    prior_outputs = [output,*sorted(p.parent for p in output.parent.glob('*/native_video.json') if p.parent!=output)]
    for prior in prior_outputs:
        cached = valid_video_manifest(root,prior/'native_video.json') if prior.exists() else None
        if (cached and cached.get('parameters')==params and cached.get('adapter')==adapter
                and all(cached['source_hashes'].get(ref)==h for ref,h in hashes.items())):
            _register(root,evidence_registry,prior)
            return {**cached['receipt'],'cached':True,'elapsed_s':time.monotonic()-started}
    if output.exists():
        # Interrupted or damaged recordings remain available for inspection.
        from uuid import uuid4
        output = output.with_name(output.name+'_'+uuid4().hex[:8])
        manifest = output/'native_video.json'
    rows = load_rows(trajectory)
    times,scheduled,indices = _schedule(rows,t_start_s,t_end_s,fps)
    ffmpeg = shutil.which('ffmpeg'); engine = None
    output.mkdir(parents=True,exist_ok=False)
    try:
        if backend=='matlab' or not ffmpeg:
            try:
                import matlab.engine
                engine = matlab.engine.start_matlab('-desktop' if backend=='matlab' else '-nodesktop')
                engine.addpath(str(CODE_ROOT/'matlab'),nargout=0)
            except Exception as exc:
                raise RuntimeError('NATIVE_BACKEND_OR_MP4_ENCODER_UNAVAILABLE: requires MATLAB for Figure rendering; MP4 requires FFmpeg/libx264 or MATLAB VideoWriter MPEG-4') from exc
        with tempfile.TemporaryDirectory(prefix='frames_',dir=output) as temporary:
            frames = Path(temporary)
            if backend=='mujoco':
                _mujoco_frames(folder,rows,indices,frames)
            else:
                from tools.matlab_replay import capture_tdcr
                {'tdcr_planar_saved_v1':capture_tdcr}[adapter](engine,folder,frames,indices,fps)
            encoding = _encode(frames,output/'video.mp4',fps,engine,ffmpeg)
            shutil.copyfile(frames/'frame_000000.png',output/'preview.png')
    finally:
        if engine is not None:
            engine.quit()  # Only the session created by this call; no waitfor/viewer.
    with (output/'video.mp4').open('rb') as f:
        if b'ftyp' not in f.read(32):
            raise ValueError('INVALID_MP4_CONTAINER')
    ref = lambda p:p.relative_to(root).as_posix()
    receipt = dict(status='completed',video_ref=ref(output/'video.mp4'),preview_ref=ref(output/'preview.png'),
                   metadata_ref=ref(manifest),backend=backend,renderer='mujoco.Renderer' if backend=='mujoco' else 'MATLAB Figure / getframe',
                   result_ref=result_ref,t_start_s=times[indices[0]],t_end_s=times[indices[-1]],fps=fps,
                   frame_count=len(indices),playback_duration_s=len(indices)/fps,cached=False,backend_solves=0,
                   elapsed_s=time.monotonic()-started)
    atomic_json(manifest,dict(**identity,receipt=receipt,source_indices=indices,
                saved_times_s=[times[i] for i in indices],scheduled_times_s=scheduled,
                interpolation=False,rescoring=False,encoding=encoding,
                sampling='Previous saved state at fixed 1/fps intervals; final frame held for 1/fps seconds.',
                artifact_hashes={ref(output/name):file_hash(output/name) for name in ('video.mp4','preview.png')}))
    atomic_json(output/'receipt.json',receipt)
    _register(root,evidence_registry,output)
    return receipt


def _register(root, registry, output):
    for p in output.iterdir():
        if p.is_file():
            registry[p.relative_to(root).as_posix()] = dict(sha256=file_hash(p))


def video_receipts(root, result_ref, backend):
    """Workbench lists matching recordings, never triggers rendering."""
    root = Path(root)
    receipts = []
    for path in sorted((root/'observations/videos').glob('*/native_video.json')):
        info = read(path)
        receipt = info.get('receipt',{})
        if receipt.get('result_ref')==result_ref and receipt.get('backend')==backend and valid_video_manifest(root.resolve(),path):
            receipts.append(receipt)
    return receipts

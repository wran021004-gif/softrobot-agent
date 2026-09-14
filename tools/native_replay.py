"""Native MuJoCo saved-state playback. No integration, control or scoring."""
import bisect
import time
from pathlib import Path
import numpy as np
import mujoco
from tools.observation_tools import load_observation
from tools.state_io import read, atomic_json
from tools.artifact_tools import file_hash


def resolve_run(source, candidate_id=None, backend='mujoco'):
    source = Path(source).resolve()
    if (source / 'state.json').exists():
        state = read(source / 'state.json')
        if state.get('version') == 'dynamic_workbench_v2':
            stop = next((d for d in reversed(state['decisions']) if d['tool']=='stop_design' and d['status']=='accepted'), {})
            cid = candidate_id or stop.get('selection', stop.get('arguments', {})).get('selected_candidate_id')
            candidate = next((c for c in state['candidates'] if c['candidate_id']==cid), None)
            if not candidate:
                raise ValueError('No explicitly selected design; supply --candidate')
            result = candidate['results'].get(backend, {})
            if not result.get('result_ref'):
                raise ValueError('NO_TRAJECTORY: selected candidate backend was not run')
            folder = (source / result['result_ref']).resolve().parent
            if not folder.is_relative_to(source):raise ValueError('Result outside campaign')
            return folder
        from tools.design_session import evaluation, summary
        best = summary(state)['best_candidate']
        cid = candidate_id or (best['candidate_id'] if best else None)
        ev = evaluation(state, cid)
        if not ev or not ev['result']['data'].get('trajectory_available'):
            raise ValueError('NO_TRAJECTORY: candidate has no saved trajectory')
        return source / ev['result']['data']['run']
    return source


class NativeReplay:
    def __init__(self, source, *, observation=None):
        self.source = Path(source).resolve()
        self.observation = observation if observation is not None else load_observation(self.source)
        if self.observation['backend'].lower() != 'mujoco':
            raise ValueError('Use the MATLAB Figure entry for MATLAB trajectories')
        self.samples = self.observation['samples']
        if not self.samples:
            raise ValueError('NO_TRAJECTORY')
        self.times = np.array([s['time_s'] for s in self.samples])
        self.model = mujoco.MjModel.from_xml_path(str(self.source / 'robot.xml'))
        self.data = mujoco.MjData(self.model)
        # Rendering colors only; the saved robot.xml remains untouched.
        colors = ((1, .65, .05, 1), (.1, .9, .5, 1), (.4, .5, 1, 1), (.95, .2, .65, 1))
        for i in range(self.model.ntendon):
            self.model.tendon_rgba[i] = colors[i % len(colors)]
        # Tendons lie inside the saved body radius. Translucent robot surfaces
        # reveal their actual routes without displacing geometry or routing.
        self.model.geom_rgba[self.model.geom_bodyid > 0] = [.38, .67, .88, .25]
        self.model.vis.headlight.active = 1
        self.model.vis.headlight.ambient[:] = [.5, .5, .5]
        self.model.vis.headlight.diffuse[:] = [.7, .7, .7]
        self.camera = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(self.model, self.camera)
        # The saved model supplies the scene center/extent, including its objects.
        self.camera.azimuth, self.camera.elevation = 115, -22
        self.option = mujoco.MjvOption()
        self.option.flags[mujoco.mjtVisFlag.mjVIS_TENDON] = True
        self.option.flags[mujoco.mjtVisFlag.mjVIS_JOINT] = False
        self.cursor, self.paused = float(self.times[0]), False
        self.seek(self.cursor)

    def seek(self, saved_time):
        self.index = max(0, min(len(self.times) - 1, bisect.bisect_right(self.times, saved_time) - 1))
        sample = self.samples[self.index]
        self.data.qpos[:] = sample['state']
        self.data.time = sample['time_s']
        self.kinematics_only(self.model, self.data)
        return self.index

    @staticmethod
    def kinematics_only(model, data):
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        mujoco.mj_tendon(model, data)

    def key(self, code):
        if code == 32:  # Space
            self.paused = not self.paused
        elif code in (262, 263):  # GLFW right/left
            self.paused = True
            self.index = min(len(self.times)-1, max(0, self.index + (1 if code == 262 else -1)))
            self.cursor = float(self.times[self.index])
        elif code == 82:  # R
            self.cursor = float(self.times[0])

    def show(self, *, seconds=None):
        import mujoco.viewer
        print('MuJoCo 保存轨迹回放：空格暂停/继续，左右键逐帧，R 回到开头；鼠标拖动旋转/平移，滚轮缩放。关闭窗口退出。', flush=True)
        print('Saved final force_n:', self.samples[-1]['force_n'], '\nSaved diagnosis:', self.source/'diagnosis.json', flush=True)
        self.seek(self.cursor)
        # Installed launch_passive initializes with mj_forward. This dedicated
        # replay process substitutes only that synchronous initialization call;
        # its passive viewer never starts a physics thread. Restore immediately.
        forward = mujoco.mj_forward
        try:
            mujoco.mj_forward = self.kinematics_only
            viewer = mujoco.viewer.launch_passive(self.model, self.data, key_callback=self.key,
                                                 show_left_ui=False, show_right_ui=False)
        finally:
            mujoco.mj_forward = forward
        with viewer:
            print('MuJoCo native window opened (passive, kinematics only).', flush=True)
            with viewer.lock():
                viewer.cam.lookat[:] = self.camera.lookat
                viewer.cam.distance = self.camera.distance
                viewer.cam.azimuth, viewer.cam.elevation = self.camera.azimuth, self.camera.elevation
                viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_TENDON] = True
            started = previous = time.monotonic()
            while viewer.is_running():
                now = time.monotonic()
                if seconds is not None and now - started >= seconds:
                    break
                if not self.paused:
                    self.cursor = min(float(self.times[-1]), self.cursor + now - previous)
                    if self.cursor >= self.times[-1]:
                        self.paused = True
                previous = now
                with viewer.lock():
                    self.seek(self.cursor)
                # state_only=True would invoke mj_forward inside the viewer.
                viewer.sync(state_only=False)
                time.sleep(.01)

    def export(self, folder, *, fps=25, width=800, height=600):
        from PIL import Image, ImageDraw
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        gif, png, manifest = (folder / name for name in ('native_scene.gif', 'native_scene.png', 'native_replay.json'))
        if any(p.exists() for p in (gif, png, manifest)):
            raise ValueError('EXPORT_EXISTS: choose a new output directory')
        self.model.vis.global_.offwidth = max(width, self.model.vis.global_.offwidth)
        self.model.vis.global_.offheight = max(height, self.model.vis.global_.offheight)
        frames, indices = [], []
        scheduled = np.arange(self.times[0], self.times[-1], 1 / fps).tolist() + [float(self.times[-1])]
        with mujoco.Renderer(self.model, height=height, width=width) as renderer:
            for t in scheduled:
                indices.append(self.seek(t))
                renderer.update_scene(self.data, self.camera, self.option)
                frame = Image.fromarray(renderer.render())
                draw = ImageDraw.Draw(frame)
                draw.rectangle((0, 0, width, 30), fill=(20, 28, 40))
                draw.text((12, 8), f'Saved MuJoCo scene | t={self.data.time:.3f} s | no simulation / no rescoring', fill='white')
                frames.append(frame)
        frames[-1].save(png)
        durations = [max(10, round((self.times[j] - self.times[i]) * 1000)) for i, j in zip(indices, indices[1:])]
        durations.append(round(1000 / fps))
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=durations, loop=0)
        atomic_json(manifest, dict(source=str(self.source), xml_sha256=file_hash(self.source / 'robot.xml'),
                                   trajectory_sha256=self.observation['source_sha256'], sample_indices=indices,
                                   saved_times_s=[float(self.times[i]) for i in indices], durations_ms=durations,
                                   interpolation=False, backend_solves=0, rescoring=False,
                                   display_only='translucent robot surfaces, tendon colors and headlight; saved model unchanged',
                                   geometry_updates=['mj_kinematics', 'mj_comPos', 'mj_tendon'],
                                   candidate_id=self.observation.get('candidate_id'), backend='mujoco',
                                   renderer='mujoco.Renderer', final_saved_tip_m=self.samples[-1]['tip_m'],
                                   final_rendered_tip_m=self.data.site_xpos[self.model.site('tip_site').id].tolist(),
                                   length_m=self.observation['design']['total_length_m'],
                                   target_m=self.observation['target_m'],
                                   target='target_site from saved robot.xml', camera=dict(azimuth=self.camera.azimuth, elevation=self.camera.elevation)))
        return [gif, png, manifest]


def main():
    import argparse
    parser = argparse.ArgumentParser(description='MuJoCo 原生场景保存轨迹回放和 GIF 导出；不启动实验')
    parser.add_argument('source', help='工作台目录或原数值运行目录')
    parser.add_argument('--candidate', help='候选编号；Round9 默认 LLM 明确选定的候选')
    parser.add_argument('--backend', choices=['mujoco','matlab'], default='mujoco')
    parser.add_argument('--export', metavar='NEW_FOLDER', help='导出原生场景 GIF、PNG 和时间映射，使用新目录')
    parser.add_argument('--show', action='store_true', help='导出后也打开原生交互窗口；MATLAB Figure 始终保持可见直至用户关闭')
    parser.add_argument('--seconds', type=float, help='MuJoCo 窗口验证时长；默认保持打开直到用户关闭')
    args = parser.parse_args()
    folder = resolve_run(args.source, args.candidate, args.backend)
    if args.backend == 'matlab':
        from tools.matlab_replay import show_matlab
        show_matlab(folder, args.export)
        return
    player = NativeReplay(folder)
    if args.export:
        print('\n'.join(str(p) for p in player.export(args.export)))
    if not args.export or args.show:
        player.cursor=float(player.times[0]);player.show(seconds=args.seconds)

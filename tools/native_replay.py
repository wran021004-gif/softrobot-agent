"""Native MuJoCo saved-state playback. No integration, control or scoring."""
import bisect
import time
from pathlib import Path
import numpy as np
import mujoco
from tools.observation_tools import load_observation
from tools.state_io import read, atomic_json
from tools.artifact_tools import file_hash


def resolve_run(source, candidate_id=None):
    source = Path(source).resolve()
    if (source / 'state.json').exists():
        from tools.design_session import evaluation, summary
        state = read(source / 'state.json')
        best = summary(state)['best_candidate']
        cid = candidate_id or (best['candidate_id'] if best else None)
        ev = evaluation(state, cid)
        if not ev or not ev['result']['data'].get('trajectory_available'):
            raise ValueError('NO_TRAJECTORY: candidate has no saved trajectory')
        return source / ev['result']['data']['run']
    return source


class NativeReplay:
    def __init__(self, source):
        self.source = Path(source).resolve()
        self.observation = load_observation(self.source)
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
        length = self.observation['design']['total_length_m']
        self.camera.lookat[:] = [length * .45, 0, .055]
        self.camera.distance = max(.6, length * 2.3)
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
        mujoco.mj_kinematics(self.model, self.data)
        mujoco.mj_comPos(self.model, self.data)
        mujoco.mj_tendon(self.model, self.data)
        return self.index

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
        self.seek(self.cursor)
        with mujoco.viewer.launch_passive(self.model, self.data, key_callback=self.key,
                                         show_left_ui=False, show_right_ui=False) as viewer:
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
                                   target='target_site from saved robot.xml', camera=dict(azimuth=self.camera.azimuth, elevation=self.camera.elevation)))
        return [gif, png, manifest]


def main():
    import argparse
    parser = argparse.ArgumentParser(description='MuJoCo 原生场景保存轨迹回放和 GIF 导出；不启动实验')
    parser.add_argument('source', help='工作台目录或原数值运行目录')
    parser.add_argument('--candidate', help='如 c001；默认最佳已评价候选')
    parser.add_argument('--export', metavar='NEW_FOLDER', help='导出原生场景 GIF、PNG 和时间映射，使用新目录')
    args = parser.parse_args()
    player = NativeReplay(resolve_run(args.source, args.candidate))
    if args.export:
        print('\n'.join(str(p) for p in player.export(args.export)))
    else:
        player.show()

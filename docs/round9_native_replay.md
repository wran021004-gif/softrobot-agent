# Round 9 native saved-trajectory playback

From `D:\softrobot-agent`, in the existing `softagent` environment:

```powershell
python examples/native_replay.py runs/round9_reach --backend mujoco
python examples/native_replay.py runs/round9_reach --backend matlab
```

Both commands default to the LLM's explicit stop selection, currently **c071**.
Use `--candidate c071` to select explicitly. Missing/null selection requires an
explicit candidate; Round9 never falls back to historical best c066. Result
folders are resolved from the candidate's backend `result_ref`, not directory hashes.

MuJoCo opens its native passive viewer with the saved `robot.xml`. Mouse controls
rotate/pan/zoom; Space pauses/resumes, arrows move one saved frame, and R rewinds.
Only `mj_kinematics`, `mj_comPos` and `mj_tendon` update the scene. The installed
viewer normally calls `mj_forward` during launch; this dedicated replay process
temporarily substitutes kinematic initialization for that one call, then restores
the function. No physics thread, integration or scoring is started. Force output
and diagnosis references come from saved records, not renderer-computed quantities.

MATLAB opens a visible desktop Figure using `matlab/tdcr_replay_saved.m`. It reads
its own backend's `trajectory.json.gz`, `shared_input.json` and `robot_ir.json`, and
uses MATLAB graphics for separate actual-radius segment capsules, saved colored
tendon routes, a fixed-base marker, floor and target. The original planar eight
joint poses are unchanged; no motion interpolation, new dynamics or Simscape is
used. Play/Pause, the time slider and MATLAB camera tools remain usable. Python
waits until the user closes the Figure before ending its MATLAB session.

The workbench `runs/round9_reach/index.html` now embeds real MATLAB Figure and
MuJoCo Renderer GIF captures for the selected design. Native-window commands are
shown separately as copyable text. Existing Canvas pages remain linked as
**轨迹示意 / 曲线 / 诊断**; the selected candidate's line animation is collapsed
below its native recording.

For a future single capture, supply a new folder (existing captures are protected):

```powershell
python examples/native_replay.py runs/round9_reach --backend mujoco --export NEW_MUJOCO_FOLDER --show
python examples/native_replay.py runs/round9_reach --backend matlab --export NEW_MATLAB_FOLDER
```

MATLAB captures the actual Figure framebuffer with `getframe` and retains the
interactive Figure after capture. MuJoCo captures via `mujoco.Renderer`; `--show`
also opens its interactive window. No desktop-launch service or custom URL scheme
is used. The workbench reads captures at
`observations/native/<candidate>/<backend>/native_scene.gif` under the campaign,
with source/timing manifests alongside them.

## Bounded validation on c071

One MATLAB Figure and one MuJoCo viewer were opened and visually checked on the
Windows desktop; both were left open for the user. Each backend produced exactly
one 51-frame GIF (about two seconds), with its final PNG and source manifest.
MATLAB's Figure was initially behind the MATLAB desktop; the same Figure was
brought forward for inspection, without reopening or rerecording it.

Target `[0.25, 0, 0.15] m`, length `0.31875 m`, eight segments of `0.03984375 m`, and
body radius `0.02 m` agree with saved inputs. Final rendered tip positions match
each backend's saved result:

- MATLAB: `[0.2507642908251862, 0, 0.14325499423936974] m`.
- MuJoCo: `[0.2508118601999629, 5.526220037358503e-18, 0.14312786815660966] m`.

New LLM requests **0**, dynamics solves **0**, scoring calls **0**. Campaign state,
budget and saved numerical inputs/results were checked unchanged. Only c071's two
auxiliary HTML pages and the workbench were refreshed. No full tests, candidate
batch replay or repeat recording was performed. Capture manifests, window
screenshots and the validation report are under
`runs/round9_reach/observations/native/c071/`.

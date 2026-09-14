# On-demand native simulation video

Current timeout semantics: public service 1.2.0 and the CLI/campaign compatibility
entry use the same bounded worker (180 s plus up to 5 s for worker termination).
The owned process tree is cleaned up; detached external services and abnormal
host filesystem/OS waits are outside that guarantee. See
[engineering closeout](engineering_closeout.md) for scope and targeted evidence.

`render_simulation_video` is registered in the actual dynamics model tool schema
and dispatch. It uses a registered `result_ref`, independent of a task directory
or candidate ID. Time bounds are optional (default: saved trajectory); `fps`
defaults to 25. Use it to answer a specific visual inspection question. A text
model receiving a file reference has **not** seen the video; numerical diagnoses
still require saved evidence. New reasons and working memory remain English via
the versioned effective prompt, including existing runs.

Example tool arguments using a real saved result (the IDs here are validation
data, not defaults):

```json
{
  "result_ref": "candidates/c071/mujoco/6020a8bd03ef/result.json",
  "backend": "mujoco",
  "t_start_s": 0.2,
  "t_end_s": 0.6,
  "fps": 10,
  "reason": "Inspect the saved motion near the floor during this interval.",
  "evidence": ["candidates/c071/mujoco/6020a8bd03ef/result.json"],
  "working_memory": {
    "findings": [],
    "unresolved": ["Does the native replay visibly show contact in this interval?"],
    "next_action": "Provide the video reference for inspection; use saved contact diagnostics for a checked conclusion."
  }
}
```

From the project directory in the existing `softagent` Python environment:

```powershell
python examples/render_simulation_video.py runs/round9_reach --result-ref candidates/c071/mujoco/6020a8bd03ef/result.json --backend mujoco --t-start-s 0.2 --t-end-s 0.6 --fps 10
python examples/render_simulation_video.py runs/round9_reach --result-ref candidates/c071/matlab/aac7d8f17f2e/result.json --backend matlab --t-start-s 0.2 --t-end-s 0.6 --fps 10
```

The human CLI records and registers only derived artifacts; it does not resume a
campaign. Runtime LLM calls use the existing submit, permission, tool-call and
attempt-receipt path with unchanged budget rules. Rendering elapsed time is
reported, with `backend_solves=0`; it is never a numerical MATLAB/MuJoCo trial.

Implementation:

- `tools/simulation_video.py`: shared result resolution, fixed-rate saved-time
  sampling, source/code hashes, cache validation, MP4 encoding and small receipts.
  Its MuJoCo adapter uses `NativeReplay` and `mujoco.Renderer` with only
  `mj_kinematics`, `mj_comPos` and `mj_tendon`. The XML supplies the entire scene.
- `tools/matlab_replay.py::capture_tdcr` and `matlab/tdcr_replay_saved.m`: the
  `matlab_tdcr_planar_dynamic_v1` adapter, selected by the saved model identifier.
  The original eight-joint restriction belongs here. Unknown models or additional
  unsupported scene bodies/obstacles fail explicitly. Add an entry/function to
  the simple adapter map for a new drawing model; the tool protocol stays unchanged.
- `matlab/encode_saved_frames.m`: MATLAB VideoWriter MPEG-4 fallback encoder for
  native PNG frames from either backend. FFmpeg/libx264 is preferred if installed.
  Missing native backend/encoder is an error, never a disguised GIF or Canvas.

Only an explicit tool/CLI call records video. The automated MATLAB Figure closes
after capture; the call quits its own engine. MuJoCo uses an offscreen Renderer
without a viewer. Interactive `examples/native_replay.py` commands remain separate.
No optimization, integration, scoring, changed results or automatic closeout
recordings occur.

Videos are stored at `<run>/observations/videos/<content-key>/video.mp4`, with
`preview.png`, `native_video.json` and `receipt.json`. Matching source bytes and
recording parameters reuse valid media. Different parameters and interrupted or
damaged outputs retain separate folders. All dependencies must be in the saved
result directory; missing/external assets are reported instead of fabricated.
The workbench embeds MP4 controls and source/metadata links. Candidate/backend
selection resolves its result reference; rendering never changes the LLM selection.

Sampling uses the preceding saved state on a fixed `1/fps` clock, without
interpolation. The receipt reports actual first/last saved times and playback
duration. The last frame is held for one frame period (five samples spanning
0.2–0.6 s produce a 0.5 s clip at 10 fps). Full source indices and timestamps live
only in metadata, never in model feedback.

Focused validation: `examples/check_simulation_video.py <run> --candidate <id>`
uses the actual request builder and dispatch, with two existing backend records
and one identical repeated call. It does not submit a model decision or consume
campaign budgets. On c071, both MP4s encoded and fully decoded successfully, each
with 5 frames; both calls returned without user interaction. The repeat reused
MuJoCo media. The full model request was 40,248 bytes. New LLM requests, backend
solves and scoring calls were all zero. Existing selection, candidates, counters
and historical evidence entries were unchanged. Results are recorded in
`runs/round9_reach/observations/video_tool_validation.json`.

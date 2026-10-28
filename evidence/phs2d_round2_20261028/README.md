# PHS-2D round 2 sealed evidence

Verdict: no feasible witness. P0-A/B pass; best valid assemblies fail performance.
No holdout force was used. The original round-1 STOP remains unchanged.

- `summary.json`: frozen protocol, all screens and dynamic sets, valid-only rankings, costs, failures, audit.
- `structures.json`: all frozen assemblies, full configurations, individual payout lengths and unloaded KKT states.
- `models/*.xml`: generated native models; directory hashes include assembly identity and, after the provenance fix, full numerical protocol.
- `store/`: original Study export, complete ledger, receipts, disposition and artifact manifest.
- `*.png` / `*.svg`: static scientific figures; `plot_data.json` retains their recorded inputs.

The original `core.export` gzip archive is split into 40 MiB chunks to fit repository file limits. Its bytes and every artifact hash are unchanged by splitting. `store/archive_manifest.json` lists ordered chunks, chunk SHA256 values and the full gzip SHA256.

From the repository root, verify without opening the live Store:

```powershell
python -m tools.phs2d_round2_export --verify
```

Reconstruct and verify into a new file with Python, without extracting arbitrary paths:

```python
from pathlib import Path
import hashlib, json, shutil
folder = Path('evidence/phs2d_round2_20261028/store')
manifest = json.loads((folder/'archive_manifest.json').read_text(encoding='utf8'))
target = folder/'reconstructed_artifacts.tar.gz'
with target.open('xb') as output:
    for part in manifest['archive_parts']:
        with (folder/part['file']).open('rb') as source:
            shutil.copyfileobj(source, output)
assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest['archive_sha256']
```

The tar contains `artifacts/<content-sha256>` plus an original session/events/calls snapshot. Artifact contents retain immutable references, request parameters, source commit, numerical protocol, internal costs and raw samples. Use the manifest's media types and SHA256 checks before interpreting an artifact. No scientific replay is required for audit.

Reproduction requires the corresponding committed native physics code, Python with NumPy/SciPy/MuJoCo 3.13.0, and the recorded candidate configuration/payout/numerical protocol. Export and plot scripts only read evidence; they do not integrate physics. The closed Study rejects additional science calls; reproducing a new physical study needs a separately authorized budget, not a reset of this Store.

XML alone is not the complete experiment: `PassiveModel` sets Newton's iteration limit to 100 and tolerance to 1e-10 after loading, applies moving material-point forces at runtime, and sets initial q from the referenced unloaded state with zero qvel. Use the recorded runner and request to reproduce these settings. XML uses implicitfast and contains its own timestep, gravity, passive tendon limits and soft-constraint parameters. Earlier XML folders could be overwritten by a numerical variant; preserve them as historical files and reconstruct the exact requested model from its configuration and numerical protocol. New folders include the full protocol in their identity.

See `docs/research/phs2d_round2_results_20261028.md` for the complete interpretation, limitations and regression results. The original archive at `evidence/phs2d_20261028` remains an explicit historical dependency for the read-only first-round diagnosis.

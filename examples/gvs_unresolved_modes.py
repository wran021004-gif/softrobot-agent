"""Localize the saved full-cell static residual and test one quadratic GVS mode."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from extensions.tendon_family.gvs_projection import _segments, discretization_jacobian
from tools.state_io import atomic_json, read


def analyze(root):
    root = Path(root)
    design = read(root / 'input.json')['robot']['structure']['data']
    physics = read(root / 'backend' / 'resolved_physics.json')
    force = read(root / 'e2_force_report.json')['raw_backend_forces']
    net = np.asarray(force['passive']) - np.asarray(force['bias']) + np.asarray(force['actuator'])
    linear = discretization_jacobian(physics, design)
    unresolved = net - linear @ np.linalg.lstsq(linear, net, rcond=None)[0]

    quadratic_columns = []
    guide_kink_columns = []
    for _, samples, _ in _segments(physics, design):
        for axis in range(2):
            column = np.zeros(len(net))
            kink_column = np.zeros(len(net))
            for sample in samples:
                x = 2 * sample['normalized_center'] - 1
                phi2 = (3 * x * x - 1) / 2
                column[sample['dofs']] = (sample['cell_length_m'] * phi2
                    * sample['principal_to_segment'].T[:, axis])
                kink_column[sample['dofs']] = (sample['cell_length_m'] * max(0, x)
                    * sample['principal_to_segment'].T[:, axis])
            quadratic_columns.append(column)
            guide_kink_columns.append(kink_column)
    quadratic = np.column_stack([linear, *quadratic_columns])
    unresolved_quadratic = net - quadratic @ np.linalg.lstsq(quadratic, net, rcond=None)[0]
    guide_kink = np.column_stack([linear, *guide_kink_columns])
    unresolved_guide_kink = net - guide_kink @ np.linalg.lstsq(guide_kink, net, rcond=None)[0]

    cells = []
    for segment in ('near', 'far'):
        bodies = physics['entity_map'][segment]['bodies']
        count = len(bodies)
        for index, body_id in enumerate(bodies):
            part = physics['parts'][body_id]
            y, z = part['dofs']
            guides = []
            if index == 0:
                guides.append('segment start / transition')
            if index == count // 2:
                guides.append('specified midpoint tendon guides')
            if index == count - 1:
                guides.append('segment end / transition')
            cells.append(dict(segment=segment, cell=index, normalized_center=(index + .5) / count,
                arc_center_m=(index + .5) * part['length_m'],
                principal_y_residual_nm=float(unresolved[y]), principal_z_residual_nm=float(unresolved[z]),
                principal_y_after_quadratic_nm=float(unresolved_quadratic[y]),
                principal_z_after_quadratic_nm=float(unresolved_quadratic[z]),
                magnitude_nm=float(np.linalg.norm(unresolved[[y, z]])), nearby_feature=guides))
    ranked = sorted(cells, key=lambda cell: cell['magnitude_nm'], reverse=True)
    guide_cells = [cell for cell in cells if cell['nearby_feature']]
    guide_energy = sum(cell['magnitude_nm'] ** 2 for cell in guide_cells)
    report = dict(full_residual_l2_nm=float(np.linalg.norm(net)),
        current_projected_component_l2_nm=float(np.linalg.norm(net - unresolved)),
        current_unresolved_l2_nm=float(np.linalg.norm(unresolved)),
        current_unresolved_fraction=float(np.linalg.norm(unresolved) / np.linalg.norm(net)),
        quadratic_unresolved_l2_nm=float(np.linalg.norm(unresolved_quadratic)),
        quadratic_reduction_fraction=float(1 - np.linalg.norm(unresolved_quadratic) / np.linalg.norm(unresolved)),
        guide_kink_unresolved_l2_nm=float(np.linalg.norm(unresolved_guide_kink)),
        guide_kink_reduction_fraction=float(1 - np.linalg.norm(unresolved_guide_kink) / np.linalg.norm(unresolved)),
        guide_or_transition_cell_energy_fraction=float(guide_energy / np.linalg.norm(unresolved) ** 2),
        top_cells=ranked[:12], cells=cells)
    atomic_json(root / 'f4_unresolved_modes.json', report)
    print('full', report['full_residual_l2_nm'], 'unresolved', report['current_unresolved_l2_nm'],
          'quadratic unresolved', report['quadratic_unresolved_l2_nm'],
          'guide kink unresolved', report['guide_kink_unresolved_l2_nm'])
    print('guide/transition energy fraction', report['guide_or_transition_cell_energy_fraction'])
    for cell in ranked[:12]:
        print(cell['segment'], cell['cell'], round(cell['arc_center_m'], 5),
              round(cell['principal_y_residual_nm'], 5), round(cell['principal_z_residual_nm'], 5),
              ', '.join(cell['nearby_feature']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='runs/gvs_static_consistency_f2_20260922')
    analyze(parser.parse_args().root)

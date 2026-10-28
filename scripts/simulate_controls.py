"""Explicit dynamics replay using the original extracted playback loop."""
import json
from pathlib import Path
from package_io import parser,locate,read,write,csv_read,namespace,compare,sha


def main():
    p=parser(__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root,folder,entry,task,mapping,model=locate(args)
    # A new output is mandatory; saved package data are never overwritten.
    args.output.mkdir(parents=True,exist_ok=False)
    from playback_kernel import playback_tensions
    design=read(root/args.benchmark/'structure.json')['design']
    spec=read(folder/'replay_spec.json');schedule=csv_read(folder/'control_schedule.csv')
    commands=[[r[c] for c in mapping['requested_tension_columns']] for r in schedule]
    raw=playback_tensions(namespace(task,design),spec['physics'],spec['scene'],commands,args.output,
        xml_path=root/args.benchmark/'robot.xml')
    errors=compare(read(folder/'original_samples.json'),raw['samples'])
    report=dict(status='consistent' if max(errors.values())<=1e-9 else 'reproduction_unverified',
        original_acceptance_unchanged=True,errors=errors,physics_steps=raw['physics_steps'],
        cost=raw['cost'],xml_sha256=sha(root/args.benchmark/'robot.xml'),
        environment_contact=raw.get('environment_contact'),rigid_tool_binding=raw.get('rigid_tool_binding'))
    write(args.output/'simulation_validation.json',report);print(json.dumps(report))


if __name__=='__main__':main()

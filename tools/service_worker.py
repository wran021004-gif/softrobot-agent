"""Private subprocess entry point; no caller-selectable import path."""
import sys
from pathlib import Path
from tools.state_io import read, atomic_json
from tools.tool_registry import service_tools, execute_binding


def main():
    path=Path(sys.argv[1]);request=read(path)
    try:
        definition=service_tools()[request['tool_id']]
        if definition.isolation!='process':raise ValueError('INVALID_WORKER_BINDING')
        data=execute_binding(definition,Path(request['root']),request['registry'],request['arguments'])
        output=dict(data=data,registry=request['registry'])
    except Exception as exc:output=dict(error=str(exc))
    atomic_json(path.parent/'worker_result.json',output)


if __name__=='__main__':main()

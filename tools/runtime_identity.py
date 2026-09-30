"""Runtime identity and fail-fast conformance for paid/expensive entry points."""
from pathlib import Path
import sys


SOFTAGENT_PYTHON = Path(r'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe')


def runtime_identity(*, executable=None, version_info=None, prefix=None):
    executable=Path(executable or sys.executable).resolve()
    version_info=version_info or sys.version_info
    prefix=Path(prefix or sys.prefix).resolve()
    return dict(sys_executable=str(executable),python_version='.'.join(map(str,version_info[:3])),
        environment_prefix=str(prefix))


def require_softagent_runtime(*, executable=None, version_info=None, prefix=None,
        expected_executable=SOFTAGENT_PYTHON):
    identity=runtime_identity(executable=executable,version_info=version_info,prefix=prefix)
    actual=Path(identity['sys_executable']); expected=Path(expected_executable).resolve()
    version=tuple((version_info or sys.version_info)[:2])
    actual_prefix=Path(identity['environment_prefix'])
    if (str(actual).casefold()!=str(expected).casefold() or version!=(3,11)
            or actual_prefix.name.casefold()!='softagent'):
        raise RuntimeError('SOFTAGENT_PYTHON_3_11_REQUIRED: run with "'+str(expected)+
            '" (actual executable='+str(actual)+', version='+identity['python_version']+
            ', prefix='+str(actual_prefix)+')')
    return identity

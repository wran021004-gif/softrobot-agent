"""Read self-contained XML through Python so Windows Unicode paths work."""
from contextlib import contextmanager
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco


def load_xml(path,assets=None):
    # Decode the original bytes, without generating or changing any model element.
    text=Path(path).read_bytes().decode('utf8')
    if assets is None and any(element.get('file') for element in ET.fromstring(text).iter()):
        raise ValueError('THIS_PORTABLE_PACKAGE_LOADER_REQUIRES_SELF_CONTAINED_XML')
    return mujoco.MjModel.from_xml_string(text,assets=assets)


@contextmanager
def portable_xml_loading():
    """Keep legacy scripts byte-identical; only adapt their filesystem input."""
    previous=mujoco.MjModel.from_xml_path
    mujoco.MjModel.from_xml_path=staticmethod(load_xml)
    try:yield
    finally:mujoco.MjModel.from_xml_path=previous

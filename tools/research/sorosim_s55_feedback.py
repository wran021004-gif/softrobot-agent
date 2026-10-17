"""Compact, explicitly scoped evidence for a later SoRoSim research study."""

from __future__ import annotations


def scoped_feedback(host, references):
    """Expose only supplied, versioned feedback packets; preserve their provenance."""
    packets = []
    for reference in references:
        value = host.store.artifact(reference)
        if isinstance(value, dict) and value.get("schema") in (
                "sorosim_s55_s5t_feedback_v1", "sorosim_s56_s5t2_feedback_v1"):
            packets.append(dict(reference=reference, evidence=value))
    return packets

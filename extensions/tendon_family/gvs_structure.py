"""Physical locations on flexible segments declared by family.design."""

from .contracts import Design, GVSStructuralLocation, Rigid, Segment


def structural_locations(design):
    design = Design.model_validate(design)
    components = {component.id: component for component in design.components}
    facts = {component.id: {0.0: {'segment_boundary'}, 1.0: {'segment_boundary'}}
             for component in design.components if isinstance(component, Segment)}

    def add(part, s, kind):
        component = components.get(part)
        if isinstance(component, Segment):
            facts[part].setdefault(float(s), set()).add(kind)
        elif isinstance(component, Rigid):
            add(component.connection.part, component.connection.s, kind)

    for component in design.components:
        if isinstance(component, Segment):
            stations = sorted(component.sections, key=lambda item: item.s)
            for index, station in enumerate(stations):
                if not 0.0 < station.s < 1.0:
                    continue
                previous = stations[index - 1].section if index else station.section
                following = stations[index + 1].section if index + 1 < len(stations) else station.section
                transition = (station.section != previous or
                              (component.interpolation == 'linear' and station.section != following))
                if transition:
                    add(component.id, station.s, 'section_transition')
        elif isinstance(component, Rigid):
            add(component.connection.part, component.connection.s, 'rigid_attachment')
        if isinstance(component, (Segment, Rigid)):
            add(component.connection.part, component.connection.s, 'component_attachment')
    for tendon in design.tendons:
        for point in tendon.points:
            add(point.attachment.part, point.attachment.s, 'tendon_' + point.role)

    return {
        name: tuple(GVSStructuralLocation(s=s, kinds=tuple(sorted(kinds)))
                    for s, kinds in sorted(locations.items()))
        for name, locations in facts.items()
    }

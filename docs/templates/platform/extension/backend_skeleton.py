"""待实现后端模板；不得将本骨架冒充已接入的仿真器。"""


class Backend:
    @staticmethod
    def check(inp, parameters, control):
        raise NotImplementedError('Validate robot/environment/channels/signals before startup')

    def compile(self, inp, registry):
        raise NotImplementedError('Convert shared description without silently dropping physics')

    def initialize(self, initial, controller):
        raise NotImplementedError('Record actual initial state and controller lifecycle')

    def run(self, *, folder, timeout_s):
        raise NotImplementedError('Return BackendResult with registered typed backend data')

    def export(self):
        raise NotImplementedError('Return already computed result; never solve again')

    def close(self):
        raise NotImplementedError('Explicitly close owned resources')

# Only add step/observe/cancel when the real backend supports them.

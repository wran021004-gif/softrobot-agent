"""待实现控制器模板；先声明具体参数、状态、输出类型和执行通道。"""


class Controller:
    def __init__(self, parameters, period_s):
        raise NotImplementedError('Bind typed parameters and control period')

    def reset(self):
        raise NotImplementedError('Begin from declared initial internal state')

    def restore(self, state):
        raise NotImplementedError('Validate and restore versioned state, do not reset')

    def command(self, time_s, observations):
        raise NotImplementedError('Check required signals/phase and produce typed actuator command')

    def checkpoint(self):
        raise NotImplementedError('Return registered Payload')

    def finish(self, interrupted=False):
        raise NotImplementedError('Record ended versus interrupted lifecycle')

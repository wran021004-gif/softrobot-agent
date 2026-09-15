"""待实现搜索器模板；驱动不拥有算法迭代节奏或随机状态。"""


class Search:
    def __init__(self, parameters):
        raise NotImplementedError('Create state from typed parameters, including RNG if needed')

    def propose(self):
        raise NotImplementedError('Only propose authorized design/control values')

    def feedback(self, score):
        raise NotImplementedError('None means incomplete/invalid; task failure may have valid score')

    def stopped(self):
        raise NotImplementedError('Own algorithm stop criteria')

    def save(self):
        raise NotImplementedError('Return registered state Payload, including RNG state')

    def restore(self, state):
        raise NotImplementedError('Validate version and resume without repeating committed trials')

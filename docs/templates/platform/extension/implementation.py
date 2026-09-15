from .contracts import Output


def execute(context, arguments):
    return Output(area_m2=arguments.length_m ** 2)

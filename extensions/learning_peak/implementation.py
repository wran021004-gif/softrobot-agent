from .contracts import PeakInput, PeakOutput


def calculate(ctx, args: PeakInput) -> PeakOutput:
    return PeakOutput(peak_n=max(abs(value) for value in args.values_n))

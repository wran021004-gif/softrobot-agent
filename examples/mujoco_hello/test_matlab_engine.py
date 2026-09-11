import matlab.engine


def main():
    print("Starting MATLAB...")

    eng = matlab.engine.start_matlab()

    eng.addpath(
        r"D:\softrobot-agent\matlab",
        nargout=0
    )

    x = 3.0

    result = eng.hello_matlab(x)

    print("Input:", x)
    print("MATLAB result:", result)

    eng.quit()


if __name__ == "__main__":
    main()
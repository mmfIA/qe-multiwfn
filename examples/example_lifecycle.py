"""Example 1: engine lifecycle.

Demonstrates that the Python wrapper can:
  - locate libqe_multiwfn.so,
  - initialize the engine,
  - query its state,
  - finalize cleanly.
"""
import qe_multiwfn as qe


def main():
    print(f"QE-Multiwfn Python package version: {qe.__version__}")
    print(f"Native library path:    {qe.NATIVE_LIBRARY_PATH}")
    print(f"Native library version: {qe.NATIVE_LIBRARY_VERSION}")
    print()

    eng = qe.Engine()
    print(f"Initial state:    {eng.state}")
    eng.initialize()
    print(f"After init:       {eng.state}")
    eng.finalize()
    print(f"After finalize:   {eng.state}")
    print()

    # Context-manager form
    print("Context-manager form:")
    with qe.Engine() as e:
        print(f"  Inside 'with': {e.state}")
    print(f"  After 'with':  {e.state}")


if __name__ == "__main__":
    main()

# File: test_cad_install.py - Purpose: This file handles Test Cad Install functionality.
import sys
print(f"Python: {sys.version}")
try:
    import numpy
    print(f"Numpy: {numpy.__version__}")
except ImportError as e:
    print(f"Numpy Error: {e}")

try:
    import build123d
    print(f"Build123d: {build123d.__version__}")
except ImportError as e:
    print(f"Build123d Error: {e}")

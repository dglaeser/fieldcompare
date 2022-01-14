"""import the fieldcompare module to be used in the tests"""

import sys
from pathlib import Path

try:
    sys.path.insert(1, str(Path(__file__).parents[1]))
    import fieldcompare
except ImportError:
    raise ImportError("Could not import fieldcompare")

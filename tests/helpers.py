import sys
import os
if sys.version[:3] < '2.7':
    import unittest2 as unittest
    unittest
else:
    import unittest
sys.path.insert(0, os.path.abspath('..'))

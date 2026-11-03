import sys
from .quick import lookup
# Unchanged rebuilds are answered from a record before the compiler loads.
if not lookup(sys.argv[1:]):
    from .cli import main
    main()

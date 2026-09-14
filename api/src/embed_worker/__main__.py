import sys

from .worker import main

try:
    main()
except KeyboardInterrupt:
    pass
except Exception as e:
    print(f"embed-worker: fatal — {e}", file=sys.stderr)
    sys.exit(1)

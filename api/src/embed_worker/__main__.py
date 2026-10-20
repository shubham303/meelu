import sys

from src.core.logging import get_logger

from .worker import main

try:
    main()
except KeyboardInterrupt:
    pass
except Exception as e:
    get_logger().error("embed_worker.startup.fatal", error=str(e))
    sys.exit(1)

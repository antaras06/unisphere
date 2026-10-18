import os
import sys

# Only monkey-patch when this file is the actual server entrypoint. Gunicorn's
# eventlet worker patches on its own, and CLI commands (flask seed / flask db)
# must not be patched or eventlet raises on interpreter shutdown.
if __name__ == "__main__" and os.getenv("SOCKETIO_ASYNC_MODE", "eventlet") == "eventlet" and "pytest" not in sys.modules:
    import eventlet

    eventlet.monkey_patch()

from app import create_app  # noqa: E402
from app.extensions import socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    socketio.run(app, host=host, port=port, debug=app.config.get("DEBUG", False), allow_unsafe_werkzeug=True)

# Logger Module

This module provides a flexible logging interface that allows users to implement their own custom loggers.

## Architecture

- `Logger` (interface.py) - Abstract base class defining the logging interface
- `DefaultLogger` (default_logger.py) - Default implementation with file/console output
- `StreamLogger` (stream_logger.py) - Base class for custom streaming implementations

## Session IDs

All loggers automatically generate and include a session ID (UUID) in their logs. This helps track related log entries across a single execution session.

## Usage Examples

### Using the Default Logger

```python
from app.logger import DefaultLogger

logger = DefaultLogger()
logger.info("Application started")
logger.debug("Processing data", item_count=42)
logger.error("Something went wrong", error_code=500)

# Get the session ID
session_id = logger.get_session_id()
```

### Implementing a Custom Logger

```python
from app.logger import Logger
import uuid

class MyCustomLogger(Logger):
    def __init__(self):
        self._session_id = str(uuid.uuid4())
    
    def get_session_id(self) -> str:
        return self._session_id
    
    def info(self, message: str, **kwargs):
        # Send to your custom logging service
        my_logging_service.send({
            "level": "INFO",
            "message": message,
            "session": self._session_id,
            **kwargs
        })
    
    def error(self, message: str, **kwargs):
        # Implement other methods...
        pass
```

### Implementing a Streaming Logger

```python
from app.logger import StreamLogger
import uuid
import json

class CloudStreamLogger(StreamLogger):
    def __init__(self, stream_endpoint: str):
        super().__init__(session_id=str(uuid.uuid4()))
        self.endpoint = stream_endpoint
    
    def _write_log(self, level: str, message: str, session_id: str, **kwargs):
        # Send log to cloud streaming service
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "session_id": session_id,
            "metadata": kwargs
        }
        requests.post(self.endpoint, json=payload)
```

## Integration

To use a custom logger in your application:

```python
from app.logger import Logger, DefaultLogger

class MyApp:
    def __init__(self, logger: Logger = None):
        self.logger = logger or DefaultLogger()
    
    def run(self):
        self.logger.info("Starting application")
        # ... your code
```

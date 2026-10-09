import json
import logging


class LoggingAuditSink:
    """Production deployments must forward records to an immutable audit store."""

    def record(self, record):
        logging.getLogger("or_trace.audit").info(json.dumps(record, sort_keys=True))

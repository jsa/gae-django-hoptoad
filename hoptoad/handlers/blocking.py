import logging

from hoptoad.api import htv2

logger = logging.getLogger(__name__)

class BlockingNotifier(object):
    """A blocking Hoptoad notifier."""

    def enqueue(self, payload, timeout):
        htv2.report(payload, timeout)

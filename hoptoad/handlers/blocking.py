import logging

from hoptoad import get_hoptoad_settings
from hoptoad.api import htv2

class BlockingNotifier(object):
    """A blocking Hoptoad notifier."""

    def __init__(self):
        self._debug = get_hoptoad_settings().get('HOPTOAD_DEBUG', False)

    def enqueue(self, payload, timeout):
        if self._debug: logging.debug("hoptoad: BlockingNotifier.enqueue")
        htv2.report(payload, timeout)

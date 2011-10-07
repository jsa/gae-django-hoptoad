import logging

from google.appengine.ext import deferred

from hoptoad import get_hoptoad_settings
from hoptoad.api import htv2

class DeferredNotifier(object):
    """An async Hoptoad notifier that uses AppEngine's deferred library."""

    def __init__(self, queue):
        self._queue = queue
        self._debug = get_hoptoad_settings().get('HOPTOAD_DEBUG', False)

    def enqueue(self, payload, timeout):
        if self._debug: logging.debug("hoptoad: DeferredNotifier.enqueue")
        task = deferred.defer(htv2.report, payload, timeout, _queue=self._queue)
        if self._debug: logging.debug("hoptoad: deferred %r" % task.name)

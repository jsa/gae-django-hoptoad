from google.appengine.ext import deferred

from hoptoad.api import htv2

class DeferredNotifier(object):
    """An async Hoptoad notifier that uses AppEngine's deferred library."""

    def __init__(self, queue):
        self._queue = queue

    def enqueue(self, payload, timeout):
        deferred.defer(htv2.report, payload, timeout, _queue=self._queue)

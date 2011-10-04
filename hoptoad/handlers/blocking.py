from hoptoad.api import htv2

class BlockingNotifier(object):
    """A blocking Hoptoad notifier."""

    def enqueue(self, payload, timeout):
        htv2.report(payload, timeout)

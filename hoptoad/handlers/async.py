from google.appengine.api import urlfetch

from hoptoad import get_hoptoad_settings
from hoptoad.api import htv2

class AsyncNotifier(object):
    """An async Hoptoad notifier."""

    def enqueue(self, payload, timeout):
        use_ssl = get_hoptoad_settings().get('HOPTOAD_USE_SSL', False)
        rpc = urlfetch.create_rpc(timeout)
        # this would be beneficial if there was eg. a middleware tracking
        # rpcs and waiting on them
#        rpc.callback = lambda: htv2._aftermath(rpc, (payload, urlfetch.create_rpc(timeout)), use_ssl)
        htv2._ride_the_toad(payload, rpc, use_ssl)

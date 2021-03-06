from itertools import ifilter

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed


__version__ = 0.3
VERSION = __version__
NAME = "gae-django-hoptoad"
URL = "https://github.com/jsa/gae-django-hoptoad"


def get_hoptoad_settings():
    hoptoad_settings = getattr(settings, 'HOPTOAD_SETTINGS', {})

    if not hoptoad_settings:
        # do some backward compatibility work to combine all hoptoad
        # settings in a dictionary
        
        # for every attribute that starts with hoptoad
        for attr in ifilter(lambda x: x.startswith('HOPTOAD'), dir(settings)):
            hoptoad_settings[attr] = getattr(settings, attr)

        if not hoptoad_settings:
            # there were no settings for hoptoad at all..
            # should probably log here
            raise MiddlewareNotUsed

    return hoptoad_settings

"""Implementations of different handlers that communicate with hoptoad in
various different protocols.
"""
import os
import imp
import pprint

from google.appengine.api.taskqueue.taskqueue import _DEFAULT_QUEUE
from django.core.exceptions import MiddlewareNotUsed
from django.utils.importlib import import_module

from hoptoad import get_hoptoad_settings
from hoptoad.handlers.async import AsyncNotifier
from hoptoad.handlers.blocking import BlockingNotifier
from hoptoad.handlers.deferred import DeferredNotifier

def get_handler(*args, **kwargs):
    """Returns an initialized handler object"""
    hoptoad_settings = get_hoptoad_settings()
    handler = hoptoad_settings.get('HOPTOAD_HANDLER', 'async')
    if handler.lower() == 'async':
        return AsyncNotifier(*args, **kwargs)
    elif handler.lower() == 'deferred':
        queue = hoptoad_settings.get('HOPTOAD_DEFERRED_QUEUE', _DEFAULT_QUEUE)
        return DeferredNotifier(queue, *args, **kwargs)
    elif handler.lower() == 'blocking':
        return BlockingNotifier(*args, **kwargs)
    else:
        _module_name, _class_name = handler.rsplit('.', 1)
        _module = import_module(_module_name)
        _class = getattr(_module, _class_name)
        return _class(*args, **kwargs)

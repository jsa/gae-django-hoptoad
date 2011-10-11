import traceback
import yaml

from django.conf import settings
from django.template.defaultfilters import slugify
from django.views.debug import get_safe_settings

from hoptoad import get_hoptoad_settings


PROTECTED_PARAMS = frozenset(get_hoptoad_settings().get('HOPTOAD_PROTECTED_PARAMS', []))

def _parse_environment(request):
    """Return an environment mapping for a notification from the given request."""
    env = dict( (str(k), str(v)) for (k, v) in get_safe_settings().items() )
    env.update( dict( (str(k), str(v)) for (k, v) in request.META.items() ) )
    
    env['REQUEST_URI'] = request.build_absolute_uri()
    
    return env

def _parse_traceback(trace):
    """Return the given traceback string formatted for a notification."""
    p_traceback = [ "%s:%d:in `%s'" % (filename, lineno, funcname)
                    for filename, lineno, funcname, _
                    in traceback.extract_tb(trace) ]
    p_traceback.reverse()
    
    return p_traceback

def _parse_message(exc):
    """Return a message for a notification from the given exception."""
    return '%s: %s' % (exc.__class__.__name__, str(exc))

def _parse_request(request):
    """Return a request mapping for a notification from the given request."""
    data = []
    def _enc_key(key):
        try:
            return str(key)
        except UnicodeEncodeError:
            return str(slugify(key).encode('ascii', 'ignore'))
    for (k, v) in request.POST.items():
        k = _enc_key(k)
        try:
            data.append((k, str(v)))
        except UnicodeEncodeError:
            data.append((k, repr(v)))
    if not data:
        for (k, v) in request.GET.items():
            k = _enc_key(k)
            try:
                data.append((k, str(v)))
            except UnicodeEncodeError:
                data.append((k, repr(v)))
    data = dict(data)
    for k in PROTECTED_PARAMS.intersection(data.keys()):
        data[k] = '********************'
    
    return data

def _parse_session(session):
    """Return a request mapping for a notification from the given session."""
    return dict( (str(k), str(v)) for (k, v) in session.items() )


def _generate_payload(request, exc=None, trace=None, message=None, error_class=None):
    """Generate a YAML payload for a Hoptoad notification.
    
    Parameters:
    request -- A Django HTTPRequest.  This is required.
    
    Keyword parameters:
    exc -- A Python Exception object.  If this is not given the
           mess parameter must be.
    trace -- A Python Traceback object.  This is not required.
    message -- A string representing the error message.  If this is not
               given, the exc parameter must be.
    error_class -- A string representing the error class.  If this is not
                   given the excc parameter must be.
    """
    p_message = message if message else _parse_message(exc)
    p_error_class = error_class if error_class else exc.__class__.__name__
    p_traceback = _parse_traceback(trace) if trace else []
    p_environment = _parse_environment(request)
    p_request = _parse_request(request)
    p_session = _parse_session(request.session)
    
    return yaml.dump({ 'notice': {
        'api_key':       settings.HOPTOAD_API_KEY,
        'error_class':   p_error_class,
        'error_message': p_message,
        'backtrace':     p_traceback,
        'request':       { 'url': request.build_absolute_uri(),
                           'params': p_request },
        'session':       { 'key': '', 'data': p_session },
        'environment':   p_environment,
    }}, default_flow_style=False)

def _ride_the_toad(payload, timeout):
    raise NotImplementedError, "If needed, imitate from htv2"

def report(payload, timeout):
    raise NotImplementedError, "If needed, imitate from htv2"

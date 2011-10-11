import logging
import sys
import traceback
from xml.dom.minidom import getDOMImplementation

from google.appengine.api import mail, urlfetch
from google.appengine.api.urlfetch_errors import DownloadError
from django.conf import settings

from hoptoad import VERSION, NAME, URL
from hoptoad import get_hoptoad_settings
from hoptoad.api.htv1 import _parse_environment, _parse_request, _parse_session
from hoptoad.api.htv1 import _parse_message

def _class_name(class_):
    return class_.__class__.__name__

def _handle_errors(request, response):
    if response:
        code = "Http%s" % response
        msg = "%(code)s: %(response)s at %(uri)s" % {
                   'code': code,
                   'response': { 'Http403': "Forbidden",
                                 'Http404': "Page not found" }[code],
                   'uri': request.build_absolute_uri()
        }
        return (code, msg)
    
    exc, inst = sys.exc_info()[:2]
    return _class_name(inst), _parse_message(inst)


def generate_payload(request_tuple):
    """Generate an XML payload for a Hoptoad notification.
    
    Parameters:
    
    request_tuple -- A tuple containing a Django HTTPRequest and a possible
                     response code.
    """
    request, response = request_tuple
    hoptoad_settings = get_hoptoad_settings()
    
    p_error_class, p_message = _handle_errors(request, response)
    
    # api v2 from: http://help.hoptoadapp.com/faqs/api-2/notifier-api-v2
    xdoc = getDOMImplementation().createDocument(None, "notice", None)
    notice = xdoc.firstChild
    
    # /notice/@version
    notice.setAttribute('version', '2.1')
    
    # /notice/api-key
    api_key = xdoc.createElement('api-key')
    api_key_data = xdoc.createTextNode(hoptoad_settings['HOPTOAD_API_KEY'])
    api_key.appendChild(api_key_data)
    notice.appendChild(api_key)
    
    # /notice/notifier/name
    # /notice/notifier/version
    # /notice/notifier/url
    notifier = xdoc.createElement('notifier')
    for key, value in zip(["name", "version", "url"], [NAME, VERSION, URL]):
        key = xdoc.createElement(key)
        value = xdoc.createTextNode(str(value))
        key.appendChild(value)
        notifier.appendChild(key)
    notice.appendChild(notifier)
    
    # /notice/error/class
    # /notice/error/message
    error = xdoc.createElement('error')
    for key, value in zip(["class", "message"], [p_error_class, p_message]):
        key = xdoc.createElement(key)
        value = xdoc.createTextNode(value)
        key.appendChild(value)
        error.appendChild(key)
    
    # /notice/error/backtrace/error/line
    backtrace = xdoc.createElement('backtrace')
    
    # i do this here because I'm afraid of circular reference..
    reversed_backtrace = list(
        reversed(traceback.extract_tb(sys.exc_info()[2]))
    )
    
    if reversed_backtrace:
        for filename, lineno, funcname, text in reversed_backtrace:
            line = xdoc.createElement('line')
            line.setAttribute('file', str(filename))
            line.setAttribute('number', str(lineno))
            line.setAttribute('method', str(funcname))
            backtrace.appendChild(line)
    else:
        line = xdoc.createElement('line')
        line.setAttribute('file', 'unknown')
        line.setAttribute('number', '0')
        line.setAttribute('method', 'unknown')
        backtrace.appendChild(line)
    error.appendChild(backtrace)
    notice.appendChild(error)
    
    # /notice/request
    xrequest = xdoc.createElement('request')
    
    # /notice/request/url -- request.build_absolute_uri()
    xurl = xdoc.createElement('url')
    xurl_data = xdoc.createTextNode(request.build_absolute_uri())
    xurl.appendChild(xurl_data)
    xrequest.appendChild(xurl)
    
    # /notice/request/component -- not sure..
    comp = xdoc.createElement('component')
    #comp_data = xdoc.createTextNode('')
    xrequest.appendChild(comp)
    
    # /notice/request/action -- action which error occured
    # ... no fucking clue..
    
    # sjl: "actions" are the Rails equivalent of Django's views
    #      Is there a way to figure out which view a request object went to
    #      (if any)?  Anyway, it's not GET/POST so I'm commenting it for now.
    
    #action = xdoc.createElement('action') # maybe GET/POST??
    #action_data = u"%s %s" % (request.method, request.META['PATH_INFO'])
    #action_data = xdoc.createTextNode(action_data)
    #action.appendChild(action_data)
    #xrequest.appendChild(action)
    
    # /notice/request/params/var -- check request.GET/request.POST
    req_params = _parse_request(request).items()
    if req_params:
        params = xdoc.createElement('params')
        for key, value in req_params:
            var = xdoc.createElement('var')
            var.setAttribute('key', key)
            value = xdoc.createTextNode(str(value))
            var.appendChild(value)
            params.appendChild(var)
        xrequest.appendChild(params)
    
    # /notice/request/session/var -- check if sessions is enabled..
    sessions = xdoc.createElement('session')
    for key, value in _parse_session(request.session).iteritems():
        var = xdoc.createElement('var')
        var.setAttribute('key', key)
        value = xdoc.createTextNode(str(value))
        var.appendChild(value)
        sessions.appendChild(var)
    xrequest.appendChild(sessions)
    
    # /notice/request/cgi-data/var -- all meta data
    cgidata = xdoc.createElement('cgi-data')
    for key, value in _parse_environment(request).iteritems():
        var = xdoc.createElement('var')
        var.setAttribute('key', key)
        value = xdoc.createTextNode(str(value))
        var.appendChild(value)
        cgidata.appendChild(var)
    xrequest.appendChild(cgidata)
    notice.appendChild(xrequest)
    
    # /notice/server-environment
    serverenv = xdoc.createElement('server-environment')
    
    # /notice/server-environment/project-root -- default to sys.path[0] 
    projectroot = xdoc.createElement('project-root')
    projectroot.appendChild(xdoc.createTextNode(sys.path[0]))
    serverenv.appendChild(projectroot)
    
    # /notice/server-environment/environment-name -- environment name? wtf..
    envname = xdoc.createElement('environment-name')
    # no idea...
    
    # sjl: This is supposed to be set to something like "test", "staging",
    #      or "production" to help you group the errors in the web interface.
    #      I'm still thinking about the best way to support this.
    
    # bmjames: Taking this from a settings variable. I personally have a
    #          different settings.py for every environment and my deploy
    #          script puts the correct one in place, so this makes sense.
    #          But even if one had a single settings.py shared among
    #          environments, it should be possible to set this variable
    #          dynamically. It would simply be the responsibility of
    #          settings.py to do it, rather than the hoptoad middleware.

    envname_text = hoptoad_settings.get('HOPTOAD_ENV_NAME', 'Unknown')
    envname_data = xdoc.createTextNode(envname_text)
    envname.appendChild(envname_data)
    serverenv.appendChild(envname)
    notice.appendChild(serverenv)
    
    return xdoc.toxml('utf-8')

def _ride_the_toad(payload, rpc, use_ssl):
    """Send a notification (an HTTP POST request) to Hoptoad.
    
    Parameters:
    payload -- the XML payload for the request from _generate_payload()
    rpc -- AppEngine RPC object for urlfetch
    
    """
    headers = { 'Content-Type': 'text/xml' }

    url_template = '%s://hoptoadapp.com/notifier_api/v2/notices'
    notification_url = url_template % ("https" if use_ssl else "http")

    # allow the settings to override all urls
    notification_url = get_hoptoad_settings().get('HOPTOAD_NOTIFICATION_URL',
                                                   notification_url)

    debug = get_hoptoad_settings().get('HOPTOAD_DEBUG', False)
    if debug: logging.debug("hoptoad: submitting notification")
    urlfetch.make_fetch_call(rpc=rpc,
                             url=notification_url,
                             payload=payload,
                             method=urlfetch.POST,
                             headers=headers)

def _aftermath(rpc, retry, use_ssl):
    debug = get_hoptoad_settings().get('HOPTOAD_DEBUG', False)
    try:
        response = rpc.get_result()
    except DownloadError, err:
        if debug:
            logging.debug(err, exc_info=1)
            logging.debug("hoptoad: failed to send notification")
    else:
        status = response.status_code

        if status == 200:
            if debug: logging.debug("hoptoad: notification sent successfully")
        elif status == 403:
            if use_ssl and get_hoptoad_settings().get('HOPTOAD_NO_SSL_FALLBACK', False):
                # if we can not use SSL, re-invoke w/o using SSL
                payload, rpc = retry
                _ride_the_toad(payload, rpc, use_ssl=False)
            # else we were not trying to use SSL but got a 403 anyway
            # something else must be wrong (bad API key?)
        elif status == 422:
            # couldn't send to hoptoad..
            if debug:
                logging.debug("hoptoad: response error 422")
                mail.send_mail_to_admins(settings.DEFAULT_FROM_EMAIL,
                                         "Hoptoad error 422",
                                         body=retry[0])
        elif status == 500:
            # hoptoad is down
            if debug: logging.debug("hoptopad: response error 500")
        else:
            if debug: logging.debug("hoptoad: response error %d" % status)

def report(payload, timeout):
    use_ssl = get_hoptoad_settings().get('HOPTOAD_USE_SSL', False)
    rpc = urlfetch.create_rpc(timeout)
    _ride_the_toad(payload, rpc, use_ssl)
    _aftermath(rpc, (payload, urlfetch.create_rpc(timeout)), use_ssl)

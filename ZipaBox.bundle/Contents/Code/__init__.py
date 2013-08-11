import fileinput
import time
from LogSucker import ReadLog

NAME = L('Title')
ART  = 'art-default.png'
ICON = 'icon-default.png'
PMS_URL = 'http://localhost:32400/library/%s'
ZIPABOX_URL = 'http://my.zipato.com/zipato-web/remoting/attribute/set?serial=%s&ep=%s&apiKey=%s&value1=%s'
PMSSERVER= 'localhost' 
#Regexps to load data from strings
LOG_REGEXP = Regex('(?P<key>\w*?)=(?P<value>\w+\w?)')

responses = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200: ('OK', 'Request fulfilled, document follows'),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted',
          'Request accepted, processing continues off-line'),
    203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    205: ('Reset Content', 'Clear input form for further input.'),
    206: ('Partial Content', 'Partial content follows.'),

    300: ('Multiple Choices',
          'Object has several resources -- see URI list'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    303: ('See Other', 'Object moved -- see Method and URL list'),
    304: ('Not Modified',
          'Document has not changed since given time'),
    305: ('Use Proxy',
          'You must use proxy specified in Location to access this '
          'resource.'),
    307: ('Temporary Redirect',
          'Object moved temporarily -- see URI list'),

    400: ('Bad Request',
          'Bad request syntax or unsupported method'),
    401: ('Unauthorized',
          'Login failed'),
    402: ('Payment Required',
          'No payment -- see charging schemes'),
    403: ('Forbidden',
          'Request forbidden -- authorization will not help'),
    404: ('Not Found', 'Nothing matches the given URI'),
    405: ('Method Not Allowed',
          'Specified method is invalid for this server.'),
    406: ('Not Acceptable', 'URI not available in preferred format.'),
    407: ('Proxy Authentication Required', 'You must authenticate with '
          'this proxy before proceeding.'),
    408: ('Request Timeout', 'Request timed out; try again later.'),
    409: ('Conflict', 'Request conflict.'),
    410: ('Gone',
          'URI no longer exists and has been permanently removed.'),
    411: ('Length Required', 'Client must specify Content-Length.'),
    412: ('Precondition Failed', 'Precondition in headers is false.'),
    413: ('Request Entity Too Large', 'Entity is too large.'),
    414: ('Request-URI Too Long', 'URI is too long.'),
    415: ('Unsupported Media Type', 'Entity body in unsupported format.'),
    416: ('Requested Range Not Satisfiable',
          'Cannot satisfy request range.'),
    417: ('Expectation Failed',
          'Expect condition could not be satisfied.'),

    500: ('Internal Server Error', 'Server got itself in trouble'),
    501: ('Not Implemented',
          'Server does not support this operation'),
    502: ('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503: ('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504: ('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505: ('HTTP Version Not Supported', 'Cannot fulfill request.'),
    }

####################################################################################################

def Start():

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)
    
    if (Prefs['sync_zipabox'] and Prefs['zipabox_serial'] is not None):
        Log('Demarrage automatique actions ZipaBox')
        Dict["monitoring"] = True
        Thread.Create(monitoring)
    
####################################################################################################
def ValidatePrefs():

    if Prefs['sync_zipabox'] and Prefs['zipabox_api_key'] is None:
        return MessageContainer("Error", "Valeur api_key non renseignee.")
        
    if Prefs['sync_zipabox'] and Prefs['zipabox_serial'] is None:
        return MessageContainer("Error", "Valeur serial non renseignee.")
        
    if Prefs['sync_zipabox'] and Prefs['zipabox_ep'] is None:
        return MessageContainer("Error", "Valeur ep non renseignee.")
    
####################################################################################################
@handler('/applications/zipabox', NAME, thumb=ICON, art=ART)
def MainMenu():

    oc = ObjectContainer()

    # Test if the user have the correct settings in the PMS.
    for setting in XML.ElementFromURL('http://'+PMSSERVER+':32400/:/prefs', errors='ignore').xpath('//Setting'):
        if setting.get('id') == 'LogVerbose':
            if setting.get('value') != 'true':
                oc.add(DirectoryObject(key=Callback(FixLogging), title=L("Attention: Parametre debugging incorrect"), summary=L("The logging is disabled on the Plex Media Server scrobbling won't work, click here to enable it."), thumb=R("icon-error.png")))
                Log('Logging is currently disabled')

    oc.add(PrefsObject(title="Parametres", summary="Configurer les parametres ZipaBox", thumb=R("icon-preferences.png")))
    return oc
    

####################################################################################################
@route('/applications/zipabox/fixlogging')
def FixLogging():
    try:
        request = HTTP.Request('http://'+PMSSERVER+':32400/:/prefs?LogVerbose=1' , method='PUT').content
        return MessageContainer("Success", "Les parametres debugging ont ete mis a jour.")
    except:
        return MessageContainer("Error", "Impossible de modifier les parametres du Plex Media Server.")


####################################################################################################
def LogPath():
    return Core.storage.abs_path(Core.storage.join_path(Core.log.handlers[1].baseFilename, '..', '..', 'Plex Media Server.log'))

####################################################################################################
@route('/applications/zipabox/monitoring')

def monitoring():
    log_path = LogPath()
    Log("LogPath='%s'" % log_path)
    log_data = ReadLog(log_path, True)
    line = log_data['line']
    exstate = ""
    
    while 1:
        if not Dict["monitoring"]: break
        else: pass

        #Lit les logs et d�tecte les changements d'�tats sur une ligne traitant d'une cl� de la librairie
        log_data = ReadLog(log_path, False, log_data['where'])
        line = log_data['line']
        log_values = dict(LOG_REGEXP.findall(line))
        key = log_values.get('key', log_values.get('ratingKey', None))
        state = log_values.get('state')
        if key is not None and state is not None and state != exstate:
            exstate = state
            Log('Detection key %s, state: %s' % (key, state))
            values = {}
            if Prefs['sync_zipabox']:
                msg_title = "Zipabox"
                msg_osd = ""
                values['api_key'] = Prefs['zipabox_api_key']
                values['serial'] =  Prefs['zipabox_serial']
                values['ep'] = Prefs['zipabox_ep']
                if state == 'playing':
                    values['valeur'] = Prefs['zipabox_playing']
                    msg_osd = Prefs['zipabox_msg_playing']
                if state == 'paused':
                    values['valeur'] = Prefs['zipabox_paused']
                    msg_osd = Prefs['zipabox_msg_paused']
                if state == 'stopped':
                    values['valeur'] = Prefs['zipabox_stopped']
                #envoi notification � l'�cran (cf param�tres)
                if Prefs['msg_client'] and msg_osd != "":
                    data_url = 'http://%s:3000/xbmcCmds/xbmcHttp?command=ExecBuiltIn(Notification(%s,%s,3000))' % (Prefs['ip_client'], msg_title, msg_osd)
                    try:
                    	json_file = HTTP.Request(data_url, data=JSON.StringFromObject(values))
                        headers = json_file.headers                  
                    except:
                        pass
                data_url = ZIPABOX_URL % (values['serial'], values['ep'], values['api_key'], values['valeur'])
                try:
                    json_file = HTTP.Request(data_url, data=JSON.StringFromObject(values))
                    headers = json_file.headers
                    result = JSON.ObjectFromString(json_file.content)
                    Log(result)
                except:
                	  pass
    return 

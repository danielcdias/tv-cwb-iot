from encryption_tools import decrypt
from prefs import prefs
from sender import Mail


class MailSender(Mail):

    def __init__(self):
        host = prefs['email']['host']
        port = prefs['email']['port']
        user = decrypt(prefs['email']['user'])
        password = decrypt(prefs['email']['pass'])
        use_tls = prefs['email']['use_tls']
        super(MailSender, self).__init__(host, port=port, username=user, password=password, use_tls=use_tls)

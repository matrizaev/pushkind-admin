class Config (object):
	SECRET_KEY = 'you-will-never-guess'
	SESSION_TYPE = 'filesystem'
	#SESSION_FILE_DIR = '/var/www2/flask_session'
	DATABASE_LOCATION = 'pushkind.db'
	DATABASE_DATE_FORMAT = '%Y-%m-%d'
	EMAIL_SMTP = 'smtp.yandex.ru'
	EMAIL_IMAP = 'imap.yandex.ru'
	EMAIL_USER = 'orders@pushkind.com'
	EMAIL_PASS = 'PushkindDotCom72'
	CABINETS_API = 'http://cabinet.pushkind.com/api/'
	CABINETS_API_KEY = 'PushkindDotCom'

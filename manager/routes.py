from manager import app

from pushkindb import PushkinDB, PRODUCT_COLUMNS
from flask import redirect, url_for, flash, render_template, Response, session, request
import datetime
import requests
import re
import pandas as pd
from urllib.parse import urlparse
from pushkemail import SendPushkindEmail
from manager.forms import SigninForm, ModifyStoreForm
from csv import QUOTE_NONE
from functools import wraps
from urllib.parse import urljoin


@app.route('/signin', methods=['GET', 'POST'])
def Signin():
	breadcrumbs = None
	form = SigninForm()
	if form.validate_on_submit():
		if form.secret.data == app.config['SECRET_KEY']:
			flash('Авторизация прошла успешно.')
			expireDate = datetime.datetime.now()
			expireDate = expireDate + datetime.timedelta(days = 1)
			session['pushkind'] = app.config['SECRET_KEY']
			return redirect(url_for('ShowIndex'), code = 302)
		else:
			flash('Вы не авторизованы!')
	return render_template('signin.html', form = form, breadcrumbs = breadcrumbs)


def LoginRequired(f):
	@wraps(f)
	def DecoratedFunction(*args, **kwargs):
		if not 'pushkind' in session or session['pushkind'] != app.config['SECRET_KEY']:
			return redirect(url_for('Signin'), code=302)
		return f(*args, **kwargs)
	return DecoratedFunction


@app.route('/', methods=['GET'])
@app.route ('/index', methods=['GET'])
@LoginRequired
def ShowIndex():
	breadcrumbs = {'Главная':url_for('ShowIndex')}
	try:
		with PushkinDB(app.config['DATABASE_LOCATION']) as db:	
			api_session = requests.Session()
			api_session.auth = ('api', app.config['CABINETS_API_KEY'])
			stores_list = api_session.get(urljoin(app.config['CABINETS_API'], 'stores')).json()
			coreStore = db.GetCoreStore()
	except:
		flash ('Не удалось получить список магазинов.')
		coreStore = None
	return render_template('index.html', stores = stores_list, coreStore = coreStore, breadcrumbs = breadcrumbs)

@app.route ('/stores/<int:storeId>/products', methods=['GET'])
@LoginRequired
def ShowStore(storeId):
	breadcrumbs = {'Главная':url_for('ShowIndex'), 'Магазин':url_for('ShowStore', storeId = storeId)}
	#try:
	api_session = requests.Session()
	api_session.auth = ('api', app.config['CABINETS_API_KEY'])
	store = api_session.get(urljoin(app.config['CABINETS_API'], 'stores/{}'.format(storeId))).json()
	modifyStoreForm = ModifyStoreForm (storeId = storeId, owner = store['owner'], section = store['section'])
	url = urljoin(app.config['CABINETS_API'], store['_links']['products'])
	print (url)
	products = api_session.get(url, params = request.args).json()
	products['_links']['next'] = products['_links']['next'].replace('/api/', '/') if products['_links']['next'] else None
	products['_links']['prev'] = products['_links']['prev'].replace('/api/', '/') if products['_links']['prev'] else None
	return render_template('store.html', store = store, products = products, modifyStoreForm = modifyStoreForm, breadcrumbs = breadcrumbs)
	#except:
	#	flash ('Невозможно отобразить информацию о магазине.')
	#	return redirect(url_for('ShowIndex'), code=302)

@app.route ('/ModifyStore', methods=['POST'])
@LoginRequired
def ModifyStore ():
	form = ModifyStoreForm ()
	if form.validate_on_submit():
		try:
			storeId = int(form.storeId.data)
			api_session = requests.Session()
			api_session.auth = ('api', app.config['CABINETS_API_KEY'])
			payload = {'section':form.section.data, 'owner':form.owner.data}
			response = api_session.put(urljoin(app.config['CABINETS_API'], 'stores/{}'.format(storeId)), json = payload)
			if response.status_code != 200:
				raise Exception()
			flash ('Изменения данных магазина успешно сохранены.')
			return redirect(url_for('ShowStore', storeId = storeId), code = 302)
		except:
			flash ('Ошибка изменения данных.')
			return redirect(url_for('ShowIndex'), code = 302)	
	

@app.route('/GetCoreProducts')
@LoginRequired
def GetCoreProducts ():
	try:
		api_session = requests.Session()
		api_session.auth = ('api', app.config['CABINETS_API_KEY'])
		csv = api_session.get(urljoin(app.config['CABINETS_API'], 'core/products')).text
		return Response (csv, mimetype='text/csv', headers = {'Content-Disposition':'attachment;filename=core.csv'})
	except:
		flash ('Ошибка получения справочника.')
		return redirect(url_for('ShowIndex'), code = 302)


@app.route ('/MailCore', methods=['POST'])
@LoginRequired
def MailCore ():
	try:
		with PushkinDB(app.config['DATABASE_LOCATION']) as db:
			products = db.GetCoreProducts()
			coreStore = db.GetCoreStore ()
		recipients = [coreStore['storesAddress']]
		csv = products.to_csv(sep = ';', index = False, encoding='utf-8')
		SendPushkindEmail (app.config['EMAIL_SMTP'], app.config['EMAIL_USER'], app.config['EMAIL_PASS'], 'Core Products.csv', recipients, 'Core Products', csv)	
		return 'Успешно.'
	except:
		return 'Ошибка.'
		

@app.route ('/GetProductsUpdates')
@LoginRequired
def GetProductsUpdates():
	try:
		with PushkinDB(app.config['DATABASE_LOCATION']) as db:
			updates = db.LoadUpdates ()
			updates.sort_values ('enable', inplace = True)
			csv = updates.to_csv(sep = ';', index = False, encoding='utf-8')
			return Response (csv, mimetype='text/csv', headers = {'Content-Disposition':'attachment;filename=updates.csv'})
	except:
		flash ('Ошибка получения справочника.')
		return redirect(url_for('ShowIndex'), code = 302)
		
@app.route ('/CheckCoreNeedUpdate', methods=['POST'])
def CheckCoreNeedUpdate():
	try:
		with PushkinDB(app.config['DATABASE_LOCATION']) as db:
			coreStore = db.GetCoreStore()
			return str(coreStore['needUpdate'])
	except:
		return 'Ошибка получения данных.'
		
		
@app.route ('/GetStatistics', defaults={'storeId': None})
@app.route ('/GetStatistics/<int:storeId>/')
@LoginRequired
def GetStatistics(storeId):
	try:
		with PushkinDB(app.config['DATABASE_LOCATION']) as db:
			stats = db.LoadStatistics (storeId)
			csv = stats.to_csv(sep = ';', index = False, encoding='utf-8')
			return Response (csv, mimetype='text/csv', headers = {'Content-Disposition':'attachment;filename=stats.csv'})
	except:
		flash ('Ошибка получения статистики.')
		return redirect(url_for('ShowIndex'), code = 302)
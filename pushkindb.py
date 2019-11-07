#!/usr/bin/python3

import sqlite3
import pandas as pd
from csv import QUOTE_NONE

PRODUCT_COLUMNS = ['productSku', 'path', 'productTitle', 'productPrice', 'productDescription', 'productPicture', 'productUrl']

class PushkinDB:

	def __init__ (self, filename = 'pushkind.db'):
		self._filename = filename
		
	def __enter__(self):
		self._db = sqlite3.connect(self._filename, isolation_level=None, timeout=1)
		self._db.row_factory = sqlite3.Row
		self._db.execute('pragma journal_mode=wal;')
		return self
		
	def GetEmailAddresses (self, storeId):
		c = self._db.execute('SELECT `emailAddress` FROM `emails` WHERE `storeId` = ?', (storeId, ))
		for r in c:
			yield dict(r)
			
	def CheckStoreEmailAddress (self, storeId, email):
		c = self._db.execute('SELECT 1 FROM `emails` WHERE `storeId` = ? AND `emailAddress` = ?', (storeId, email))
		data = c.fetchall()
		if len (data) == 0:
			return False
		else:
			return True
			
	def GetStores (self):
		c = self._db.execute('SELECT * FROM `stores`')
		for r in c:
			yield dict(r)
			
	def MakeOrderFromStore (self, storeId):
		self._db.execute('INSERT OR IGNORE INTO `stats` (`date`, `storeId`, `count`) VALUES (date("now"), ?, 0)', (storeId, ))
		self._db.execute('UPDATE OR IGNORE `stats` SET `count` = `count` + 1 WHERE `date` = date ("now") and `storeId` = ?', (storeId, ))
		self._db.commit()
			
	def SetStore (self, storeId, owner, storeTitle, rootCategory):
		self._db.execute('UPDATE `stores` SET `owner` = ?, `storeTitle` = ?, `rootCategory` = ? WHERE `storeId` = ?', (owner, storeTitle, rootCategory, storeId))
		self._db.commit()
			
	def GetStoreById (self, storeId):
		c = self._db.execute('SELECT * FROM `stores` WHERE `storeId` = ? LIMIT 1', (storeId, ))
		data = c.fetchall()
		if len (data) > 0:
			return dict(data[0])
		else:
			return None
			
	def GetStoreByURL (self, storeUrl):
		c = self._db.execute('SELECT * FROM `stores` WHERE `storeUrl` = ? LIMIT 1', (storeUrl, ))
		data = c.fetchall()
		if len (data) > 0:
			return dict(data[0])
		else:
			return None
	
	def ShowStoresInfo (self):
		c = self._db.execute('SELECT `s`.`storeId`, `s`.`storeUrl`, `e`.`emailAddress`  FROM `emails` AS `e` INNER JOIN `stores` as `s` ON `s`.`storeId` = `e`.`storeId` ORDER BY `s`.`storeId`')
		data = c.fetchall()
		return data
			
	def GetCoreStore (self):
		c = self._db.execute('SELECT * FROM `core` LIMIT 1')
		data = c.fetchall()
		if len (data) > 0:
			return dict(data[0])
		else:
			return None
			
	def AddStore (self, storeId, storeUrl, appUrl):
		self._db.execute('INSERT INTO `stores` ("storeId","storeUrl","appUrl") VALUES (?, ?, ?)', (storeId, storeUrl, appUrl))
		query = f'CREATE TABLE IF NOT EXISTS `{storeId}` ("productUrl" TEXT,"path" TEXT,"productSku" TEXT,"productTitle" TEXT,"productPrice" REAL,"productDescription" TEXT,"productPicture" TEXT)'
		self._db.execute(query)
		self._db.commit()
		
	def RemoveStore (self, storeId):
		self._db.execute('DELETE FROM `stores` WHERE `storeId` = ?', (storeId, ))
		self._db.commit()
		self._db.execute(f'DROP TABLE IF EXISTS `{storeId}`')
		self._db.commit()
		self._db.execute(f'DELETE FROM `emails` WHERE `storeId` = ?', (storeId, ))
		self._db.commit()
		
	def AddEmailAddress (self, storeId, email):
		self._db.execute('INSERT INTO `emails` ("storeId","emailAddress") VALUES (?, ?)', (storeId, email))
		self._db.commit()
		
	def RemoveEmailAddress (self, storeId, email):
		self._db.execute('DELETE FROM `emails` WHERE `storeId` = ? AND `emailAddress` = ?', (storeId, email))
		self._db.commit()
		
	def SaveProducts (self, storeId, products):
		query = f'DELETE FROM `{storeId}`'
		self._db.execute(query)
		products.to_sql (storeId, self._db, if_exists = 'append', index = False)
		
	def SaveUpdates (self, updates):
		query = 'DELETE FROM `updates`'
		self._db.execute(query)
		updates.to_sql ('updates', self._db, if_exists = 'append', index = False)
		query = 'UPDATE `core` SET `needUpdate` = 1'
		self._db.execute(query)
		self._db.commit()
		
	def LoadUpdates (self):
		query = 'SELECT * FROM `updates` ORDER BY `productSku`'
		updates = pd.read_sql (query, self._db)
		query = 'UPDATE `core` SET `needUpdate` = 0'
		self._db.execute(query)
		self._db.commit()
		return updates	
		
	def LoadProducts (self, storeId):
		try:
			query = f'SELECT * FROM `{storeId}` ORDER BY `productSku`'
			products = pd.read_sql (query, self._db, columns = PRODUCT_COLUMNS)
		except:
			products = pd.DataFrame(columns = PRODUCT_COLUMNS)
		return products
		
	def LoadStatistics (self, storeId = None):
		if storeId is None:
			query = 'SELECT * FROM `stats` ORDER BY `date`'
			
		else:
			query = f'SELECT `date`, `count` FROM `stats` WHERE `storeId` = {storeId} ORDER BY `date`'
		stats = pd.read_sql (query, self._db)
		return stats
		
	def GetCoreProducts (self):
		products = pd.DataFrame(columns = PRODUCT_COLUMNS)
		for store in self.GetStores():
			query = 'SELECT CASE WHEN `a`.`productSku` IS NULL THEN "no" ELSE "yes" END AS `enable`,  "{}-" || `s`.`productSku` as `productSku`, "{}" || `s`.`path` as `path`, `s`.`productTitle` as `productTitle`, ifnull(`a`.`productPrice`,`s`.`productPrice`) as `productPrice`, `s`.`productDescription` as `productDescription`,' \
					' `s`.`productPicture` as `productPicture`, `s`.`productUrl` as `productUrl` FROM `source` as `s` LEFT JOIN `{}` as `a` ON `s`.`productSku` = `a`.`productSku` ORDER BY `s`.`productSku`'
			query = query.format (store['storeId'], store['rootCategory'], store['storeId'])
			storeProducts = pd.read_sql (query, self._db, columns = PRODUCT_COLUMNS)
			products = products.append (storeProducts, ignore_index=True, sort=False)
		products.sort_values ('productSku', inplace = True)
		products.reset_index (inplace = True, drop = True)
		return products
		
	def GetStoreSKUs (self, storeId):
		try:
			query = f'SELECT DISTINCT(`productSku`) FROM `{storeId}`'
			c = self._db.execute(query)
			for r in c:
				yield dict(r)
		except:
			return
			
	def GetProductBySKU (self, storeId, sku):
		query = f'SELECT * FROM `{storeId}` WHERE productSku = ? LIMIT 1'
		c = self._db.execute(query, (sku, ))
		data = c.fetchall()
		if len (data) > 0:
			return dict(data[0])
		else:
			return None
			
	def GetSKUStore (self, sku):
		storeId = None
		for store in self.GetStores():
			query = 'SELECT 1 FROM `{}` WHERE `productSku` = "{}" LIMIT 1'.format (store['storeId'], sku)
			try:
				c = self._db.execute(query)
				data = c.fetchall()
				if len (data) == 0:
					continue
				else:
					storeId = store['storeId']
					break
			except:
				continue
		return storeId
		
	def __exit__(self, type, value, traceback):
		if self._db:
			self._db.close()
		
		
def main():
	with PushkinDB() as db:
		store = db.GetCoreStore ()
		products = db.LoadProducts (store['storeId'])
		products[['productTitle', 'productSku', 'productPrice', 'productPicture', 'path']].to_csv('test.csv', sep = ';', quoting = QUOTE_NONE, index = False, encoding='utf-8')

		
if __name__ == '__main__': main()

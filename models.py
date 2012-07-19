#coding: utf8
import redis

import web
import config
import hashlib

okbuydb = None
redisDb = None

def getUserInfo():
	session = web.config.get('_session')
	return session.get("userInfo",False)


def save_sale_info(product_name, starttime, endtime, start_money, per_add_money,product_desc):
	userInfo = getUserInfo()
	if not userInfo:
		return {"rsCode":-1, "Msg":"用户未登录"}
	rdb = getRedisDb()

	info_id = rdb.incr(config.redisdb_config['product_key'])
	
	rdb.lpush(config.redisdb_config['saleids_key'], info_id)
	saleInfo = {
			"info_id":info_id,
			"product_name":product_name,
			"starttime":starttime,
			"endtime":endtime,
			"start_money":start_money,
			"per_add_money":per_add_money,
			"product_desc":product_desc
		}
	rdb.hmset(config.redisdb_config['sale_info_pre']+str(info_id),saleInfo)
	
	rdb.lpush(config.redisdb_config['account_sales_pre']+str(userInfo.get('ID')), info_id)

	saleInfo['infoId'] = info_id
	saleInfo['rsCode'] = 1
	return saleInfo

def getUserSaleInfo(userId):
	rdb = getRedisDb()
	saleIds = rdb.lrange(config.redisdb_config['account_sales_pre']+str(userId),0,-1)
	saleInfos = []
	if len(saleIds)>0:
		pipe = rdb.pipeline()
		for saleId in saleIds:
			pipe.hgetall(config.redisdb_config['sale_info_pre']+str(saleId))
		saleInfos = pipe.execute()
	return saleInfos

def getUserBuyInfo(userId):
	rdb = getRedisDb()
	buyIds = rdb.lrange(config.redisdb_config["account_buy_pre"]+str(userId), 0, -1)
	buyInfos = []
	if len(buyIds)>0:
		pipe = rdb.pipeline()
		for saleId in buyIds:
			pipe.hgetall(config.redisdb_config['sale_info_pre']+str(saleId))
		buyInfos = pipe.execute()
	return buyInfos

def getokbuydb():
	global okbuydb
	if not okbuydb:
		okbuydb = web.database(dbn="mysql",user=config.userdb["user"],pw=config.userdb["pw"],
				db=config.userdb["db"],host=config.userdb["host"])
	return okbuydb

def checkUser(username, password):
	db = getokbuydb()
	checkrs = db.where('Admin', Name=username, Pwd=hashlib.md5(password).hexdigest())
	users = checkrs.list()
	if len(users)!=1:
		return False
	else:
		return users[0]

def getLatestSale(num=3):
	rdb = getRedisDb()
	saleIds = rdb.lrange(config.redisdb_config["saleids_key"], 0, num)

	return getSaleInfos(saleIds)
	
def getSaleInfos(saleIds):
	rdb = getRedisDb()
	saleInfos = []
	if len(saleIds)>0:
		pipe = rdb.pipeline()
		for saleId in saleIds:
			pipe.hgetall(config.redisdb_config['sale_info_pre']+str(saleId))
		saleInfos = pipe.execute()

	return saleInfos

def getRedisDb():
	global redisDb
	if not redisDb:
		redisDb = redis.Redis()
	return redisDb





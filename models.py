#coding: utf8
import redis

import web
import config
import hashlib

import time

okbuydb = None
redisDb = None

def getAuctionLock(id):
	rdb = getRedisDb()
	lockKey = config.redisdb_config['sale_lock_pre']+str(id)
	for i in range(0,10):
		t = rdb.incr(lockKey)
		if 1==t:
			rdb.expire(lockKey, 10)
			return True
		time.sleep(1)

	return false

	
def releaseAuctionLock(id):
	rdb = getRedisDb()
	t = rdb.set(config.redisdb_config['sale_lock_pre']+str(id), 0)
	return True

def getUserInfo():
	session = web.config.get('_session')
	return session.get("userInfo",False)


def getMaxAuctionPr(infoId):
	saleInfos = getSaleList(infoId)
	if len(saleInfos)<1:
		return 0
	return int(saleInfos[0])

def addSaleList(infoId, pr):
	rdb = getRedisDb()
	userInfo = getUserInfo()
	userId = userInfo.get("ID")
	userName = userInfo.get("Name")
	saveKey = config.redisdb_config['salepr_list_pre']+str(infoId)
	rdb.lpush(saveKey, userName)
	rdb.lpush(saveKey, userId)
	rdb.lpush(saveKey, pr)
	return True

def getSaleList(infoId):
	rdb = getRedisDb()
	saleInfos = rdb.lrange(config.redisdb_config['salepr_list_pre']+str(infoId), 0, 30)
	return saleInfos

def getStatRef(saleInfo):
	nowTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
	if nowTime < saleInfo.get("starttime"):
		return {"Stat":1, "Msg":"等待拍卖开始"}

	if nowTime > saleInfo.get("endtime"):
		return {"Stat":2, "Msg":"拍卖时间已过"}

	return {"Stat":3, "Msg":"正在拍卖"}


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
			"product_desc":product_desc,
			"sale_user_id":userInfo.get('ID')
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





#coding:utf8
import sys
sys.path.append("./lib")
import web
import json
import hashlib

import rediswebpy
import models
import views
import config

import time

from functools import wraps

urls = (
	    '/', 'index',
		'/login(/.*)?','login',
		'/logout','logout',
		'/product/(\d*)', 'product',

		'/account/sale/?','account_sale',
		'/account/sale/(\d*)','account_sale',
		
		'/account/add_sale/?', 'add_sale',
		'/account/alter_sale/(\d*)','alter_sale',

		'/account/buy/?','account_buy',
		'/account/buy/(\d*)','account_buy',
	)

okbuydb = None
app = web.application(urls, globals())

web.config.debug = False
if web.config.get('_session') is None:
	session = web.session.Session(app, rediswebpy.RedisStore(), initializer={'count': 0})
	web.config._session = session
else:
	session = web.config._session

render = web.template.render('templates/')

def required_login(f=None,redirect = True):
	def decorator(func):
		@wraps(func)
		def wrapper(req,*args,**kwds):
			global session
			user = session.get("islogin",False)
			if user == False:
				paths = web.ctx.homepath + web.ctx.fullpath
				if redirect:
					raise web.seeother("/login%s" % (paths))
				else:
					return json.dumps({"rsCode":-5, "Msg":"您需要登陆后再进行该操作"})
			else:
				return func(req, *args, **kwds)
		return wrapper
	return decorator

#产品
class product():
	def GET(self, saleId):
		saleId = int(saleId)
		if saleId<=0:
			return "编号错误"
		
		saleInfos = models.getSaleInfos([saleId])

		if len(saleInfos)<1:
			return "未找到拍品信息"

		return render.base(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.show_detail(saleInfos[0]))

	@required_login()
	def POST(self, saleId):
		#获取锁
		if not models.getAuctionLock(saleId):
			return json.dumps({"Msg":"获取锁失败", "rsCode":-10})
		#
		try:
			rs = self._setpr(saleId)
			models.releaseAuctionLock(saleId)
			return rs
		except Exception,e:
			#解锁
			models.releaseAuctionLock(saleId)
			return json.dumps({"rsCode":-12, "Msg":"价格设置失败"})


	def _setpr(self, saleId):
		input = web.input()
		saleInfos = models.getSaleInfos([saleId])
		if len(saleInfos)<1:
			return {"Msg":"未找到拍品信息", "rsCode":-7}
		saleInfo = saleInfos[0]

		#状态是否正常 =todo
		#时间是否正常
		nowTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))
		if nowTime < saleInfo.get("starttime"):
			return {"Msg":"拍卖时间未到", "rsCode":-8}

		if nowTime > saleInfo.get("endtime"):
			return {"Msg":"拍卖时间已过", "rsCode":-9}

		
		#检查是否高于起拍价格
		salePr = input.get("pr")
		try:
			salePr = int(salePr)
			startMoney = saleInfo.get("start_money", 0)
			startMoney = int(startMoney)
			if salePr <= startMoney:
				return {"Msg":"人不能太小气, 价格都低于起拍价了 ...", "rsCode":-12}
		except Exception, e:
			return {"Msg":"hi, 价格必须为数字, 请检查价格 ... ", "rsCode": -11}

		#查找当前最高价查看是否高于当前价格
		
		#查看是否满足最低加价要求
		pass



class add_sale():
	@required_login()
	def GET(self):
		return render.base(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.add_sale())
	@required_login()
	def POST(self):
		input = web.input()
		save_rs = models.save_sale_info(
				input.get("product_name",""),
				input.get("starttime",""),
				input.get("endtime",""),
				input.get("start_money",""),
				input.get("per_add_money",""),
				input.get("product_desc","")
				)
		return json.dumps(save_rs)

class account_sale:
	@required_login()
	def GET(self, id=0):
		if id>0:
			return self.show_one(id)
		else:
			return self.list()

	@required_login()
	def list(self):
		userId = session.userInfo.get("ID")
		saleInfos = models.getUserSaleInfo(userId)
		
		return render.base(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.list_sale(saleInfos))


	@required_login()
	def show_one(self,sale_id):
		return sale_id

class account_buy:
	@required_login()
	def GET(self):
		return self.list()
	
	@required_login()
	def list(self):
		userId = session.userInfo.get("ID")
		buyInfos = models.getUserBuyInfo(userId)

		return render.base(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.list_buy(buyInfos))


class index:
	def GET(self,name=''):
		latestSales = models.getLatestSale(3)
		return render.base(islogin = session.get('islogin',False), userInfo = session.get('userInfo',False), 
				page=views.index_data(latestSales))

	def POST(self):
		pass

class login:
	def POST(self, jumpPath=''):
		input = web.input(username=None, password=None)
		if not input.username or not input.password:
			return json.dumps({"Msg":"用户名或密码为空, 请检查!","rsCode":-1})
		checkrs = models.checkUser(input.username, input.password)
		if not checkrs:
			return json.dumps({"Msg":"用户名或密码错误, 请检查!","rsCode":-2})
		else:
			#set session
			session.islogin = True
			session.userInfo = checkrs
			return json.dumps({"Msg":"登陆成功", "rsCode":1})

	def GET(self, jumpPath = '/'):
		return render.base(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.login_form(jumpPath))



class logout:
	def GET(self):
		session.islogin = False
		raise web.seeother('/')
if __name__ == "__main__":
	app.run()

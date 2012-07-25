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

web.config.session_parameters['cookie_name'] = 'futoubangid'
#web.config.session_parameters['cookie_domain'] = 'localhost'
web.config.session_parameters.timeout = 86400*2 #24 * 60 * 60, # 24 hours   in seconds
#web.config.session_parameters['ignore_expiry'] = True
#web.config.session_parameters['ignore_change_ip'] = True
web.config.session_parameters['secret_key'] = 'fLjUfxqXtfNoIldA0A0J'
web.config.session_parameters['expired_message'] = 'Session expired'
web.config.session_parameters['httponly'] = False

urls = (
	    '/', 'index',
		'/login(/.*)?','login',
		'/logout','logout',

		'/product/(\d*)', 'product',
		'/product/get_salelist/(\d*)', 'product_sale',

		'/account/sale/?','account_sale',
		'/account/sale/(\d*)','account_sale',
		
		'/account/add_sale/?', 'add_sale',
		'/account/alter_sale/(\d*)','alter_sale',

		'/account/buy/?','account_buy',
		'/account/buy/(\d*)','account_buy',
	
		'/img_upload', 'img_upload',

		'/account/add_sale_r/?', 'add_sale_requirejs',
		'/account/add_sale_c/?', 'add_sale_controllerjs',
		'/account/add_sale_l/?', 'add_sale_lazy',
	)

okbuydb = None
app = web.application(urls, globals())

web.config.debug = False
if web.config.get('_session') is None:
	session = web.session.Session(app, rediswebpy.RedisStore(initial_flush=False), initializer={'count': 0})
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
class img_upload():
	def POST(self):
		x = web.input()
		session._load(x.get("futoubangid"))
		filename = "123.jpg"
		filedir = "/tmp/up/"+filename
		fp = open(filedir,'w')
		fp.write(x.myfile)
		print session.get('userInfo',False)
		fp.close()
		return 'OK'
class product_sale:
	def GET(self,saleId):
		saleId = int(saleId)
		if saleId<=0:
			return "编号错误"
		saleLists = models.getSaleList(saleId)
		rs = ''
		saleLen = len(saleLists)
		for i in range(0,saleLen/3):
			rs += "<div>%s %s</div>" % (saleLists[i*3+2], saleLists[i*3])
		return rs
#产品
class product():
	def GET(self, saleId):
		saleId = int(saleId)
		if saleId<=0:
			return "编号错误"
		
		saleInfos = models.getSaleInfos([saleId])

		if len(saleInfos)<1:
			return "未找到拍品信息"


		statRef = models.getStatRef(saleInfos[0])

		return render.base(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.show_detail(saleInfos[0], statRef))

	@required_login(redirect=False)
	def POST(self, saleId):
		#获取锁
		if not models.getAuctionLock(saleId):
			return json.dumps({"Msg":"获取锁失败", "rsCode":-10})
		#
		try:
			rs = self._setpr(saleId)
			models.releaseAuctionLock(saleId)
			return json.dumps(rs)
		except Exception,e:
			#解锁
			print e
			models.releaseAuctionLock(saleId)
			return json.dumps({"rsCode":-120, "Msg":"价格设置失败"})


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
		maxAuctionPr = models.getMaxAuctionPr(saleId)
		if maxAuctionPr >= salePr:
			return {"rsCode":-13, "Msg":"你的报价已经比别人低了!"}
		#查看是否满足最低加价要求
		perAddMoney = saleInfo.get("per_add_money",0)
		perAddMoney = int(perAddMoney)
		if (salePr-maxAuctionPr) <  perAddMoney:
			return {"rsCode":-14, "Msg":"最低加价额度是: "+str(perAddMoney)}
		#拍卖者本人不能加价
		userInfo = session.get('userInfo',False)
		if str(userInfo.get("ID")) == str(saleInfo.get("sale_user_id")):
			return {"rsCode":-14, "Msg":"物品拍卖者自己不能加价!"}
			
		#save the money
		models.addSaleList(saleId, salePr)
		return {"rsCode":1, "Msg":"success: "+str(salePr)}


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
				input.get("starttime-hour",""),
				input.get("endtime",""),
				input.get("endtime-hour",""),
				input.get("start_money",""),
				input.get("per_add_money",""),
				input.get("product_desc","")
				)
		return json.dumps(save_rs)
class add_sale_requirejs():
	@required_login()
	def GET(self):
		return render.base_r(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.add_sale())
class add_sale_controllerjs():
	@required_login()
	def GET(self):
		return render.base_c(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.add_sale())
class add_sale_lazy():
	@required_login()
	def GET(self):
		return render.base_l(islogin = session.get('islogin',False), 
				userInfo = session.get('userInfo',False), 
				page=views.add_sale())


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
		#print web.cookies().get("webpy_session_id")
		latestSales = models.getLatestSale(20)
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

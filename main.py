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

from functools import wraps

urls = (
		    '/', 'index',
			'/login(/.*)?','login',
			'/logout','logout',

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
					return back_json_data({"rsCode":-5, "Msg":"您需要登陆后再进行该操作"})
			else:
				return func(req, *args, **kwds)
		return wrapper
	return decorator

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
		return render.base(islogin = session.get('islogin',False), userInfo = session.get('userInfo',False), page=views.index_data())

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

#coding:utf8
import sys
sys.path.append("./lib")
import web
import json
import hashlib

import rediswebpy
import views
import config

urls = (
		    '/', 'index',
			'/login','login',
			'/logout','logout',
			'/account/sale/?','account_sale',
			'/account/sale/(\d*)','account_sale',
			'/account/buy/?','account_buy',
			'/account/buy/(\d*)','account_buy',

			'/account/add_sale/?', 'add_sale',
			'/account/alter_sale/(\d*)','alter_sale',
	   )

okbuydb = None
app = web.application(urls, globals())

web.config.debug = False
if web.config.get('_session') is None:
	session = web.session.Session(app, rediswebpy.RedisStore(), initializer={'count': 0})
	web.config._session = session
else:
	session = web.config._session


def getokbuydb():
	global okbuydb
	if not okbuydb:
		okbuydb = web.database(dbn="mysql",user=config.userdb["user"],pw=config.userdb["pw"],
				db=config.userdb["db"],host=config.userdb["host"])
	return okbuydb

class add_sale():
	def GET(self):
		pass
	def POST(self):
		pass

class account_sale:
	def GET(self, id=0):
		if id>0:
			return self.show_one(id)
		else:
			return self.list()

	def list(self):
		return "list"

	def show_one(self,sale_id):
		return sale_id

class account_buy:
	def GET(self):
		pass

class index:
	def GET(self,name=''):
		render = web.template.render('templates/')
		return render.base(islogin = session.get('islogin',False), userInfo = session.get('userInfo',False), page=views.index_data())

class login:
	def POST(self):
		input = web.input(username=None, password=None)
		if not input.username or not input.password:
			return json.dumps({"Msg":"用户名或密码为空, 请检查!","rsCode":-1})
		checkrs = self.checkUser(input.username, input.password)
		if not checkrs:
			return json.dumps({"Msg":"用户名或密码错误, 请检查!","rsCode":-2})
		else:
			#set session
			session.islogin = True
			session.userInfo = checkrs

			return json.dumps({"Msg":"登陆成功", "rsCode":1})

	def checkUser(self, username, password):
		db = getokbuydb()
		checkrs = db.where('Admin', Name=username, Pwd=hashlib.md5(password).hexdigest())
		users = checkrs.list()
		if len(users)!=1:
			return False
		else:
			return users[0]
class logout:
	def GET(self):
		session.islogin = False
		raise web.seeother('/')
if __name__ == "__main__":
	app.run()

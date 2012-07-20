#coding: utf8
import web
import config

t_globals = dict(
	datestr = web.datestr
)
render = web.template.render('templates/',  
		    globals=t_globals)
def index_data(latestSales):
	return render.index(latestSales)

def add_sale():
	return render.add_sale()

def list_sale(saleInfos):
	return render.my_sale_list(saleInfos)

def list_buy(buyInfos):
	return render.my_buy_list(buyInfos)

def login_form(jumpPath):
	return render.login_form(jumpPath)

def show_detail(saleInfo, statRef):
	return render.show_detail(saleInfo, statRef)

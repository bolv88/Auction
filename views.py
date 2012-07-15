#coding: utf8
import web
import config

t_globals = dict(
	datestr = web.datestr
)
render = web.template.render('templates/',  
		    globals=t_globals)
def index_data():
	return render.index()

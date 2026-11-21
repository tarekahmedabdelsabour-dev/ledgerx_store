import frappe

from ledgerx_store import data, web


def get_context(context):
	web.base(context)
	s = context.store
	context.hero_title = s.hero_title or s.store_name
	context.featured, _t = data.listing(featured=True)
	if len(context.featured) < 4:
		context.featured = (context.featured + data.listing()[0])[:8]
	context.featured = context.featured[:8]
	context.news = data.news(3) if s.show_news else []
	context.cars = data.cars(4)
	context.rooms = data.rooms()[:3]

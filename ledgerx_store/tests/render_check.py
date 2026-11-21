"""Renders every store template with made-up data and a stub of the site layout. Run: python3 -m ledgerx_store.tests.render_check"""
import datetime
import glob
import os
import types

import jinja2

ROOT = os.path.join(os.path.dirname(__file__), "..")
STUB = """<html><head>{% block head_include %}{% endblock %}</head><body>{% block navbar %}{% endblock %}{% block content %}{% endblock %}{% block footer %}{% endblock %}</body></html>"""


def env():
	e = jinja2.Environment(loader=jinja2.ChoiceLoader([jinja2.DictLoader({"templates/web.html": STUB}), jinja2.PrefixLoader({"ledgerx_store": jinja2.FileSystemLoader(ROOT)})]), autoescape=False)
	e.globals["_"] = lambda s, *a: s
	return e


class D(dict):
	__getattr__ = dict.get


def base():
	store = D(store_name="Demo", primary_color="#0B2A5B", accent_color="#E8A317", logo="", phone="+20100", whatsapp="2010", email="a@b.co", address="Cairo", working_hours="9-5",
		footer_text="Hi", menu=[D(url="/p/x", label="X")], transfer_instructions="Acct 1", hero_text="Text", tagline="Tag")
	frappe = types.SimpleNamespace(session=types.SimpleNamespace(user="Guest"), lang="ar", format_date=lambda d: str(d))
	return dict(store=store, frappe=frappe, currency="EGP", title="T", description="d", image="", cats=[D(name="Cat", store_slug="cat", store_image="")], menu_pages=[D(title="About", slug="about")],
		has_news=True, has_cars=True, has_rooms=True, whatsapp_link="https://wa.me/2010", money=lambda v: f"{v:.2f} EGP", q="", cat="", sort="new", page=1)


ITEM = {"code": "A", "name": "Panadol", "image": "", "slug": "panadol", "price": 25.5, "in_stock": True, "summary": "s", "group": "Cat", "featured": 1, "detail": "500 mg tablet"}


def contexts():
	b = base()
	car = D(name="CAR-1", make="Kia", model="Rio", year=2022, mileage=40000, color="Red", fuel="Petrol", transmission="Automatic", engine_cc=1600, condition="Used", asking_price=650000, image="", notes="n")
	room = D(name="RT-1", room_type_name="Deluxe", hotel="H", max_adults=2, max_children=1, beds="1 King", description="d", from_rate=1200.0, currency="EGP")
	so = D(name="SO-1", status="To Deliver and Bill", per_delivered=0, store_payment_method="Bank Transfer", store_payment_status="Unpaid", delivery_date=datetime.date(2026, 11, 25), grand_total=100.0)
	item = D(name="A", item_name="Panadol", image="", item_group="Cat", price=25.5, in_stock=True, store_summary="s", ph_is_drug=1, ph_strength="500 mg", ph_form="Tablet")
	return {
		"store": dict(b, featured=[ITEM] * 8, news=[D(name="n1", title="T", blog_intro="i", meta_image="")], cars=[car], rooms=[room], hero_title="Hello"),
		"shop": dict(b, items=[ITEM] * 3, total=3, pages=2, cat_title="Cat", base_query="q=x"),
		"product": dict(b, item=item, related=[ITEM], group_slug="cat", detail_html="<p>x</p>"),
		"cart": b,
		"checkout": dict(b, methods=["Cash on Delivery", "Bank Transfer"], prefill={}),
		"order": dict(b, so=so, lines=[D(item_name="Panadol", qty=2, amount=51.0)], address_text="Cairo"),
		"my-orders": dict(b, orders=[D(name="SO-1", store_key="k", transaction_date="2026-11-21", grand_total=10, status="Draft", store_payment_status="Unpaid")]),
		"contact-us": b,
		"news": dict(b, posts=[D(name="n1", title="T", blog_intro="i", meta_image="", published_on="2026-11-01")]),
		"news_post": dict(b, post=D(title="T", published_on="2026-11-01", meta_image=""), body="<p>b</p>"),
		"page": dict(b, page_doc=D(title="About", image="", body="<p>b</p>")),
		"cars": dict(b, cars=[car]),
		"car": dict(b, car=car),
		"stay": dict(b, rooms=[room]),
	}


def main():
	e, bad = env(), 0
	for name, ctx in contexts().items():
		t = e.get_template(f"ledgerx_store/www/{name}.html")
		out = t.render(**ctx)
		ok = len(out) > 400 and "Demo" in out
		print(("ok  " if ok else "FAIL"), name, len(out))
		bad += not ok
	files = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, "www", "*.html"))}
	missing = files - set(contexts())
	print("not rendered:", missing or "none")
	raise SystemExit(1 if bad or missing else 0)


if __name__ == "__main__":
	main()

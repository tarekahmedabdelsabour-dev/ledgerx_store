"""Shared context for every store page."""
import frappe
from frappe.utils import fmt_money

from ledgerx_store import __version__, data


def base(context, title=None, description=None, image=None):
	s = data.settings()
	if not s.enabled and frappe.session.user == "Guest":
		raise frappe.PermissionError
	context.no_cache = 1
	context.show_sidebar = 0
	context.no_breadcrumbs = 1
	context.store = s
	context.v = __version__
	context.currency = frappe.db.get_value("Price List", s.price_list, "currency") or frappe.db.get_value("Company", s.company, "default_currency")
	context.title = f"{title} | {s.store_name}" if title else s.store_name
	context.description = description or s.meta_description or s.tagline or ""
	context.image = image or s.logo
	context.cats = data.categories()
	context.menu_pages = data.menu_pages()
	context.has_news = bool(s.show_news and data.news(1))
	context.has_cars = bool(data.cars(1))
	context.has_rooms = data.has_rooms()
	context.whatsapp_link = f"https://wa.me/{''.join(ch for ch in (s.whatsapp or '') if ch.isdigit())}" if s.whatsapp else ""
	context.money = lambda v: fmt_money(v, currency=context.currency)
	return context


def money(value, currency):
	return fmt_money(value, currency=currency)


import math

import frappe
from frappe import _

from ledgerx_store import data, web


def get_context(context):
	web.base(context, _("Shop"))
	f = frappe.form_dict
	q, cat, sort, page = (f.get("q") or "").strip(), f.get("cat") or "", f.get("sort") or "new", int(f.get("page") or 1)
	rows, total = data.listing(q, cat, page, sort)
	per = max(1, context.store.items_per_page or 24)
	context.items, context.total, context.q, context.cat, context.sort, context.page = rows, total, q, cat, sort, page
	context.pages = max(1, math.ceil(total / per))
	context.cat_title = frappe.db.get_value("Item Group", {"store_slug": cat}, "name") if cat else None
	context.base_query = "&".join(f"{k}={v}" for k, v in (("q", q), ("cat", cat), ("sort", sort)) if v)

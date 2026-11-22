import math
from urllib.parse import urlencode

import frappe
from frappe import _

from ledgerx_store import data, web


def get_context(context):
	web.base(context, _("Shop"))
	f = frappe.form_dict
	q, cat, sort = (f.get("q") or "").strip()[:60], f.get("cat") or "", f.get("sort") or "new"
	try:
		page = max(1, int(f.get("page") or 1))
	except (TypeError, ValueError):
		page = 1
	rows, total = data.listing(q, cat, page, sort)
	per = max(1, context.store.items_per_page or 24)
	context.items, context.total, context.q, context.cat, context.sort, context.page = rows, total, q, cat, sort, page
	context.pages = max(1, math.ceil(total / per))
	context.cat_title = frappe.db.get_value("Item Group", {"store_slug": cat}, "name") if cat else None
	context.base_query = urlencode([(k, v) for k, v in (("q", q), ("cat", cat), ("sort", sort)) if v])
	context.q_url = urlencode({"q": q}) if q else ""

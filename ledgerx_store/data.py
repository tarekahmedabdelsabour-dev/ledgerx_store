"""Reads the database for the store: settings, catalog, stock, prices, categories."""
import frappe
from frappe.utils import flt, nowdate

from ledgerx_store.engine import cart

CACHE_SECS = 60


def settings():
	return frappe.get_cached_doc("Store Settings")


def warehouses():
	return [w.warehouse for w in settings().warehouses or []]


def tax_rate():
	t = settings().sales_taxes_template
	if not t:
		return 0.0
	rows = frappe.get_all("Sales Taxes and Charges", filters={"parent": t, "charge_type": "On Net Total"}, fields=["rate"])
	return sum(flt(r.rate) for r in rows)


def _has_doctype(name):
	return bool(frappe.db.exists("DocType", name))


def price_of(items):
	"""{item_code: selling price} from the store price list, newest valid price wins."""
	if not items:
		return {}
	pl = settings().price_list
	rows = frappe.db.sql(
		"""select item_code, price_list_rate from `tabItem Price`
		where price_list = %s and selling = 1 and item_code in %s
		and (valid_from is null or valid_from <= %s) and (valid_upto is null or valid_upto >= %s)
		order by valid_from asc""", (pl, tuple(items), nowdate(), nowdate()), as_dict=True)
	out = {}
	for r in rows:
		out[r.item_code] = flt(r.price_list_rate)
	return out


def stock_of(items):
	"""{item_code: available qty or None when the item is not stocked}. Expired batches are not counted."""
	if not items:
		return {}
	meta = {r.name: r for r in frappe.get_all("Item", filters={"name": ["in", list(items)]}, fields=["name", "is_stock_item", "has_batch_no", "has_expiry_date"])}
	whs = warehouses()
	out = {}
	plain = [i for i in items if meta.get(i) and meta[i].is_stock_item and not (meta[i].has_batch_no and meta[i].has_expiry_date)]
	if plain and whs:
		rows = frappe.db.sql(
			"select item_code, sum(actual_qty - reserved_qty) q from `tabBin` where warehouse in %s and item_code in %s group by item_code", (tuple(whs), tuple(plain)), as_dict=True)
		got = {r.item_code: flt(r.q) for r in rows}
		for i in plain:
			out[i] = got.get(i, 0.0)
	for i in items:
		m = meta.get(i)
		if not m or not m.is_stock_item:
			out[i] = None
		elif m.has_batch_no and m.has_expiry_date:
			out[i] = _fresh_batch_qty(i, whs)
	return out


def _fresh_batch_qty(item, whs):
	try:
		from erpnext.stock.doctype.batch.batch import get_batch_qty

		today, total = nowdate(), 0.0
		for wh in whs:
			for b in get_batch_qty(item_code=item, warehouse=wh) or []:
				exp = frappe.db.get_value("Batch", b.get("batch_no"), "expiry_date")
				if not exp or str(exp) >= today:
					total += flt(b.get("qty"))
		return total
	except Exception:
		frappe.log_error(title=f"Store: batch stock for {item}")
		return 0.0


def _sellable(row):
	if row.get("ph_is_drug") is None:
		return True
	if row.get("ph_is_drug") and not settings().show_pharmacy:
		return False
	return cart.sellable_pharmacy(row.get("ph_is_drug"), row.get("ph_class"))


def item_fields():
	fields = ["name", "item_name", "item_group", "image", "description", "store_slug", "store_summary", "store_featured", "store_max_qty", "store_backorder", "stock_uom", "brand"]
	if frappe.get_meta("Item").has_field("ph_is_drug"):
		fields += ["ph_is_drug", "ph_class", "ph_strength", "ph_form"]
	return fields


def catalog(codes):
	"""Everything the cart needs about the given items, keyed by item code."""
	rows = frappe.get_all("Item", filters={"name": ["in", list(codes)], "disabled": 0, "store_publish": 1, "is_sales_item": 1}, fields=item_fields())
	prices, stock = price_of([r.name for r in rows]), stock_of([r.name for r in rows])
	return {r.name: {"price": prices.get(r.name), "stock": stock.get(r.name), "max_qty": r.store_max_qty or None, "name": r.item_name, "backorder": r.store_backorder,
		"sellable": _sellable(r), "image": r.image, "slug": r.store_slug, "uom": r.stock_uom} for r in rows}


def categories():
	return frappe.get_all("Item Group", filters={"store_visible": 1}, fields=["name", "store_slug", "store_image", "parent_item_group"], order_by="store_sort asc, name asc")


def _group_and_children(slug):
	g = frappe.db.get_value("Item Group", {"store_slug": slug, "store_visible": 1}, ["name", "lft", "rgt"], as_dict=True)
	if not g:
		return None
	return [r for r in frappe.get_all("Item Group", filters={"lft": [">=", g.lft], "rgt": ["<=", g.rgt]}, pluck="name")]


def listing(q="", category="", page=1, sort="new", featured=False):
	"""-> (rows, total). Rows carry price, stock state, slug and image."""
	s = settings()
	filters = {"disabled": 0, "store_publish": 1, "is_sales_item": 1}
	or_filters = None
	if category:
		groups = _group_and_children(category)
		if groups is None:
			return [], 0
		filters["item_group"] = ["in", groups]
	if featured:
		filters["store_featured"] = 1
	if q:
		like = f"%{q.strip()[:60]}%"
		or_filters = {"item_name": ["like", like], "name": ["like", like], "description": ["like", like]}
	fields = item_fields()
	order = {"new": "creation desc", "name": "item_name asc"}.get(sort, "creation desc")
	rows = frappe.get_all("Item", filters=filters, or_filters=or_filters, fields=fields, order_by=order, limit_page_length=2000)
	rows = [r for r in rows if _sellable(r)]
	codes = [r.name for r in rows]
	prices = price_of(codes)
	rows = [r for r in rows if prices.get(r.name)]
	if sort in ("price_asc", "price_desc"):
		rows.sort(key=lambda r: prices[r.name], reverse=(sort == "price_desc"))
	total = len(rows)
	per = max(1, s.items_per_page or 24)
	page = max(1, int(page or 1))
	rows = rows[(page - 1) * per: page * per]
	stock = stock_of([r.name for r in rows])
	out = []
	for r in rows:
		st = stock.get(r.name)
		out.append({"code": r.name, "name": r.item_name, "image": r.image, "slug": r.store_slug or cart.slugify(r.item_name, r.name), "price": prices[r.name],
			"in_stock": st is None or st > 0 or bool(r.store_backorder), "summary": r.store_summary, "group": r.item_group, "featured": r.store_featured,
			"detail": " ".join(x for x in (r.get("ph_strength"), r.get("ph_form")) if x)})
	return out, total


def product(slug):
	row = frappe.db.get_value("Item", {"store_slug": slug, "store_publish": 1, "disabled": 0}, item_fields(), as_dict=True)
	if not row or not _sellable(row):
		return None
	price = price_of([row.name]).get(row.name)
	if not price:
		return None
	st = stock_of([row.name]).get(row.name)
	row.update({"price": price, "stock": st, "in_stock": st is None or st > 0 or bool(row.store_backorder), "web_description": frappe.db.get_value("Item", row.name, "web_long_description") if frappe.get_meta("Item").has_field("web_long_description") else None})
	return row


def related(item_group, exclude, n=4):
	rows, _t = listing(category=frappe.db.get_value("Item Group", item_group, "store_slug") or "", page=1)
	return [r for r in rows if r["code"] != exclude][:n]


def menu_pages():
	return frappe.get_all("Store Page", filters={"published": 1, "in_menu": 1}, fields=["title", "slug"], order_by="sort_order asc, title asc")


def news(limit=6):
	if not _has_doctype("Blog Post"):
		return []
	f = {"published": 1}
	cat = settings().news_category
	if cat:
		f["blog_category"] = cat
	return frappe.get_all("Blog Post", filters=f, fields=["name", "title", "blog_intro", "meta_image", "published_on"], order_by="published_on desc", limit_page_length=limit)


def cars(limit=60):
	if not _has_doctype("Car") or not settings().show_cars:
		return []
	return frappe.get_all("Car", filters={"store_publish": 1, "status": "Ready for Sale"}, fields=["name", "make", "model", "year", "mileage", "color", "fuel", "transmission", "condition", "asking_price", "image"], order_by="modified desc", limit_page_length=limit)


def rooms():
	if not _has_doctype("Room Type") or not settings().show_hotels:
		return []
	out = []
	for rt in frappe.get_all("Room Type", filters={"store_publish": 1}, fields=["name", "room_type_name", "hotel", "max_adults", "max_children", "beds", "description"]):
		low = frappe.db.sql(
			"""select min(rate_room_only) r, currency from `tabRate Plan` where room_type = %s and enabled = 1 and applicable_to = 'Public'
			and (valid_from is null or valid_from <= %s) and (valid_to is null or valid_to >= %s)""", (rt.name, nowdate(), nowdate()), as_dict=True)
		rt["from_rate"] = flt(low[0].r) if low and low[0].r else None
		rt["currency"] = low[0].currency if low else None
		out.append(rt)
	return out

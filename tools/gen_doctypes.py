"""Builds the DocType JSON files of ledgerx_store. Run from the repo root: python3 tools/gen_doctypes.py (controller .py files are never overwritten)."""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "ledgerx_store", "store", "doctype")
TS = "2026-11-22 12:00:00.000000"
MODULE = "Store"


def f(name, ftype, label=None, **kw):
	d = {"fieldname": name, "fieldtype": ftype}
	if ftype not in ("Section Break", "Column Break", "Tab Break"):
		d["label"] = label or name.replace("_", " ").title()
	elif label:
		d["label"] = label
	d.update(kw)
	return d


def sec(name, label=None, **kw):
	return f(name, "Section Break", label, **kw)


def col(name):
	return f(name, "Column Break")


MGR = "Store Manager"


def perms(*rows):
	out = []
	for role, mode in rows:
		p = {"role": role, "read": 1, "report": 1, "print": 1, "export": 1}
		if mode in ("rw", "all"):
			p["write"] = 1
		if mode == "all":
			p.update({"create": 1, "delete": 1})
		if mode == "rwc":
			p.update({"write": 1, "create": 1})
		out.append(p)
	out.append({"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "print": 1, "export": 1})
	return out


DT = {}
KINDS = "Contact\nTest Drive\nCar Interest\nHotel Booking\nService"
PAY = "Cash on Delivery\nBank Transfer\nOnline Payment"

DT["Store Warehouse"] = {"istable": 1, "fields": [f("warehouse", "Link", "Warehouse", options="Warehouse", reqd=1, in_list_view=1)], "perms": [], "autoname": "hash", "icon": "", "title_field": ""}
DT["Store Link"] = {"istable": 1, "fields": [
	f("label", "Data", "Label", reqd=1, in_list_view=1), f("url", "Data", "Address", reqd=1, in_list_view=1, description="For example /shop or /p/about.")],
	"perms": [], "autoname": "hash", "icon": "", "title_field": ""}

DT["Store Settings"] = {"issingle": 1, "fields": [
	f("enabled", "Check", "Store Is Open", default=1),
	f("store_name", "Data", "Store Name", reqd=1),
	f("tagline", "Data", "Tagline"),
	f("logo", "Attach Image", "Logo"),
	col("cb0"),
	f("primary_color", "Color", "Main Color", default="#0B2A5B"),
	f("accent_color", "Color", "Accent Color", default="#E8A317"),
	f("make_home_page", "Check", "Use the Store as the Home Page of the Website"),
	sec("sb_sell", "Selling"),
	f("company", "Link", "Company", options="Company", reqd=1),
	f("price_list", "Link", "Price List", options="Price List", reqd=1, description="Only items with a price in this list can be sold."),
	f("warehouses", "Table", "Warehouses That Fill Online Orders", options="Store Warehouse", description="Stock of these warehouses is what the store shows."),
	f("customer_group", "Link", "Customer Group for New Customers", options="Customer Group"),
	f("territory", "Link", "Territory for New Customers", options="Territory"),
	col("cb1"),
	f("sales_taxes_template", "Link", "Sales Taxes Template", options="Sales Taxes and Charges Template"),
	f("shipping_fee", "Currency", "Shipping Fee", default=0),
	f("free_shipping_over", "Currency", "Free Shipping Above", default=0, description="0 = never free."),
	f("shipping_account", "Link", "Shipping Income Account", options="Account", description="Required when the shipping fee is more than zero."),
	f("min_order", "Currency", "Minimum Order", default=0),
	f("delivery_days", "Int", "Delivery Takes (days)", default=3),
	f("auto_submit_orders", "Check", "Submit Orders Automatically", default=1, description="Off: the order stays a draft until a person checks it."),
	sec("sb_pay", "Payment"),
	f("cod_enabled", "Check", "Cash on Delivery", default=1),
	f("transfer_enabled", "Check", "Bank Transfer or Wallet", default=0),
	f("transfer_instructions", "Small Text", "Transfer Instructions", description="Account number, wallet number, and what to write in the transfer note."),
	f("online_gateway", "Select", "Online Payment", options="None\nPaymob", default="None"),
	f("online_mode_of_payment", "Link", "Mode of Payment for Online Payments", options="Mode of Payment"),
	col("cb2"),
	f("paymob_api_key", "Password", "Paymob API Key"),
	f("paymob_integration_id", "Data", "Paymob Integration ID"),
	f("paymob_iframe_id", "Data", "Paymob Frame ID"),
	f("paymob_hmac_secret", "Password", "Paymob HMAC Secret", description="The callback address to give Paymob is shown in the install guide."),
	sec("sb_show", "What the Store Shows"),
	f("show_pharmacy", "Check", "Sell Over-the-counter Pharmacy Products", default=1, description="Prescription and controlled drugs are never sold online."),
	f("show_cars", "Check", "Show Cars for Sale", default=0),
	f("show_hotels", "Check", "Show Hotel Rooms", default=0),
	f("show_news", "Check", "Show News", default=1),
	f("items_per_page", "Int", "Products per Page", default=24),
	sec("sb_home", "Home Page"),
	f("hero_title", "Data", "Main Headline"),
	f("hero_text", "Small Text", "Short Text under It"),
	sec("sb_contact", "Contact and Footer"),
	f("phone", "Data", "Phone"),
	f("whatsapp", "Data", "WhatsApp Number", description="With country code, digits only."),
	f("email", "Data", "Email"),
	col("cb3"),
	f("address", "Small Text", "Address"),
	f("working_hours", "Data", "Working Hours"),
	f("footer_text", "Small Text", "Footer Text"),
	sec("sb_menu", "Menu"),
	f("menu", "Table", "Extra Menu Links", options="Store Link"),
	sec("sb_alerts", "Notifications"),
	f("notify_role", "Link", "Tell This Role About New Orders", options="Role", default="Store Manager"),
	f("meta_description", "Small Text", "Description for Search Engines"),
], "perms": perms((MGR, "rw"), ("Sales Manager", "r"))}

DT["Store Page"] = {"fields": [
	f("title", "Data", "Title", reqd=1, in_list_view=1),
	f("slug", "Data", "Address Part", reqd=1, unique=1, in_list_view=1, description="The page opens at /p/<this>."),
	f("published", "Check", "Published", default=1, in_list_view=1),
	f("in_menu", "Check", "Show in the Menu", default=0),
	f("sort_order", "Int", "Order in the Menu", default=0),
	col("cb1"),
	f("image", "Attach Image", "Top Image"),
	f("summary", "Small Text", "Summary"),
	sec("sb_body", "Content"),
	f("body", "Text Editor", "Content"),
], "autoname": "field:slug", "icon": "fa fa-file-text-o", "title_field": "title", "perms": perms((MGR, "all"))}

DT["Store Post"] = {"fields": [
	f("title", "Data", "Title", reqd=1, in_list_view=1),
	f("slug", "Data", "Address Part", reqd=1, unique=1, in_list_view=1, description="The post opens at /news/<this>."),
	f("published", "Check", "Published", default=1, in_list_view=1),
	f("published_on", "Date", "Published On", default="Today", in_list_view=1),
	col("cb1"),
	f("image", "Attach Image", "Top Image"),
	f("summary", "Small Text", "Summary"),
	sec("sb_body", "Content"),
	f("body", "Text Editor", "Content"),
], "autoname": "field:slug", "icon": "fa fa-newspaper-o", "title_field": "title", "perms": perms((MGR, "all"))}

DT["Store Inquiry"] = {"fields": [
	f("kind", "Select", "Kind", options=KINDS, reqd=1, in_list_view=1, in_standard_filter=1),
	f("status", "Select", "Status", options="New\nContacted\nClosed", default="New", in_list_view=1, in_standard_filter=1),
	f("full_name", "Data", "Name", reqd=1, in_list_view=1),
	f("phone", "Data", "Phone", in_list_view=1),
	col("cb1"),
	f("email", "Data", "Email"),
	f("lead_doctype", "Link", "Lead Type", options="DocType", read_only=1, hidden=1),
	f("lead", "Dynamic Link", "Lead", options="lead_doctype", read_only=1),
	f("ref_doctype", "Data", "About (Type)", read_only=1),
	f("ref_name", "Data", "About", read_only=1),
	sec("sb_d", "Details"),
	f("date_from", "Date", "From"),
	f("date_to", "Date", "To"),
	f("guests", "Int", "Guests"),
	col("cb2"),
	f("message", "Text", "Message"),
	f("handled_note", "Small Text", "Our Notes"),
], "autoname": "format:INQ-.YYYY.-.#####", "icon": "fa fa-comments", "title_field": "full_name", "perms": perms((MGR, "all"), ("Sales User", "rw"), ("Sales Manager", "rw"))}


def build():
	os.makedirs(ROOT, exist_ok=True)
	for name, d in DT.items():
		fields = d["fields"]
		out = {
			"actions": [], "creation": TS, "doctype": "DocType", "engine": "InnoDB", "field_order": [x["fieldname"] for x in fields],
			"fields": fields, "links": [], "modified": TS, "modified_by": "Administrator", "module": MODULE, "name": name, "owner": "Administrator",
			"sort_field": "creation", "sort_order": "DESC", "states": [], "permissions": d["perms"], "allow_rename": 0,
		}
		for k in ("autoname", "icon", "title_field", "issingle", "istable"):
			if d.get(k):
				out[k] = d[k]
		if not d.get("istable") and not d.get("issingle"):
			out["track_changes"] = 1
		slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
		folder = os.path.join(ROOT, slug)
		os.makedirs(folder, exist_ok=True)
		open(os.path.join(folder, "__init__.py"), "a").close()
		with open(os.path.join(folder, slug + ".json"), "w", encoding="utf-8") as fh:
			json.dump(out, fh, indent=1, ensure_ascii=False)
			fh.write("\n")
		py = os.path.join(folder, slug + ".py")
		if not os.path.exists(py):
			cls = "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", name))
			open(py, "w").write(f"from frappe.model.document import Document\n\n\nclass {cls}(Document):\n\tpass\n")


if __name__ == "__main__":
	build()
	print(len(DT), "doctypes")

import frappe
from frappe import _

from ledgerx_store import data, web


def get_context(context):
	item = data.product(frappe.form_dict.get("slug"))
	if not item:
		raise frappe.DoesNotExistError
	web.base(context, item.item_name, item.store_summary, item.image)
	context.item = item
	context.related = data.related(item.item_group, item.name)
	context.group_slug = frappe.db.get_value("Item Group", item.item_group, "store_slug")
	context.detail_html = item.web_description or item.description or ""

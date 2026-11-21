import frappe

from ledgerx_store import web


def get_context(context):
	p = frappe.db.get_value("Store Page", {"slug": frappe.form_dict.get("slug"), "published": 1}, ["title", "summary", "image", "body"], as_dict=True)
	if not p:
		raise frappe.DoesNotExistError
	web.base(context, p.title, p.summary, p.image)
	context.page_doc = p

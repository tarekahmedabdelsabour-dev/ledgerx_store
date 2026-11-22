import frappe
from frappe.utils import nowdate

from ledgerx_store import web


def get_context(context):
	name = frappe.form_dict.get("slug")
	post = frappe.db.get_value("Store Post", {"name": name, "published": 1, "published_on": ["<=", nowdate()]}, ["name", "title", "summary", "image", "published_on", "body"], as_dict=True) if name else None
	if not post:
		raise frappe.DoesNotExistError
	web.base(context, post.title, post.summary, post.image)
	context.post = post

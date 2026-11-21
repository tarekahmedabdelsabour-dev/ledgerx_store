import frappe
from frappe import _

from ledgerx_store import web


def get_context(context):
	web.base(context, _("Checkout"))
	s = context.store
	context.methods = [m for m, on in (("Cash on Delivery", s.cod_enabled), ("Bank Transfer", s.transfer_enabled), ("Online Payment", s.online_gateway not in (None, "", "None"))) if on]
	context.prefill = {}
	if frappe.session.user != "Guest":
		u = frappe.db.get_value("User", frappe.session.user, ["full_name", "email", "mobile_no"], as_dict=True) or {}
		context.prefill = {"name": u.get("full_name"), "email": u.get("email"), "phone": u.get("mobile_no")}

import frappe
from frappe import _

from ledgerx_store import orders, web


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/my-orders"
		raise frappe.Redirect
	web.base(context, _("My orders"))
	custs = orders.customers_of_user(frappe.session.user)
	context.orders = frappe.get_all("Sales Order", filters={"customer": ["in", custs or [""]], "store_order": 1, "docstatus": ["<", 2]},
		fields=["name", "transaction_date", "grand_total", "status", "per_delivered", "store_payment_status", "store_key", "currency"], order_by="creation desc", limit_page_length=50)

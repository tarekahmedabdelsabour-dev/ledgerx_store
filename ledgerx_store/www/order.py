import frappe
from frappe import _

from ledgerx_store import orders, web


def get_context(context):
	web.base(context, _("Your order"))
	name, key = frappe.form_dict.get("id"), frappe.form_dict.get("k")
	if not name or not orders.can_view(name, key, frappe.session.user):
		raise frappe.PermissionError
	so = frappe.db.get_value("Sales Order", name, ["name", "transaction_date", "delivery_date", "status", "grand_total", "total_taxes_and_charges", "net_total", "per_delivered", "per_billed", "docstatus",
		"store_payment_method", "store_payment_status", "customer_name", "store_phone", "currency", "shipping_address"], as_dict=True)
	context.so = so
	context.lines = frappe.get_all("Sales Order Item", filters={"parent": name}, fields=["item_name", "qty", "rate", "amount", "image"], order_by="idx")
	context.address_text = frappe.utils.strip_html(so.shipping_address or "")
	context.currency = so.currency

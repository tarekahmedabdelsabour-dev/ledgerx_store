import frappe
from frappe.utils import add_to_date, now_datetime


def hourly():
	"""Online orders nobody paid within a day go to Failed so staff can call or cancel them."""
	try:
		cutoff = add_to_date(now_datetime(), hours=-24)
		for n in frappe.get_all("Sales Order", filters={"store_order": 1, "store_payment_status": "Pending", "creation": ["<", cutoff], "docstatus": ["<", 2]}, pluck="name"):
			frappe.db.set_value("Sales Order", n, "store_payment_status", "Failed", update_modified=False)
	except Exception:
		frappe.log_error(title="Store: hourly job failed")

"""Install and migrate steps. Each is idempotent and a failing step never aborts a migrate."""
import os

import frappe

MODULE, FOLDER = "Store", "store"
ROLES = ["Store Manager"]
FIELDS = [
	("Item", "store_section", {"label": "Online Store", "fieldtype": "Section Break", "insert_after": "item_name", "collapsible": 1}),
	("Item", "store_publish", {"label": "Show in the Online Store", "fieldtype": "Check", "insert_after": "store_section", "in_standard_filter": 1}),
	("Item", "store_featured", {"label": "Feature on the Home Page", "fieldtype": "Check", "insert_after": "store_publish", "depends_on": "store_publish"}),
	("Item", "store_slug", {"label": "Address Part", "fieldtype": "Data", "insert_after": "store_featured", "depends_on": "store_publish", "no_copy": 1, "description": "Filled for you from the name."}),
	("Item", "store_col", {"fieldtype": "Column Break", "insert_after": "store_slug"}),
	("Item", "store_summary", {"label": "Short Description for the Store", "fieldtype": "Small Text", "insert_after": "store_col", "depends_on": "store_publish"}),
	("Item", "store_max_qty", {"label": "Most per Order", "fieldtype": "Int", "insert_after": "store_summary", "depends_on": "store_publish"}),
	("Item", "store_backorder", {"label": "Sell Even When Out of Stock", "fieldtype": "Check", "insert_after": "store_max_qty", "depends_on": "store_publish"}),
	("Item Group", "store_visible", {"label": "Show in the Online Store", "fieldtype": "Check", "insert_after": "parent_item_group"}),
	("Item Group", "store_slug", {"label": "Store Address Part", "fieldtype": "Data", "insert_after": "store_visible", "depends_on": "store_visible", "no_copy": 1}),
	("Item Group", "store_image", {"label": "Store Image", "fieldtype": "Attach Image", "insert_after": "store_slug", "depends_on": "store_visible"}),
	("Item Group", "store_sort", {"label": "Store Order", "fieldtype": "Int", "insert_after": "store_image", "depends_on": "store_visible"}),
	("Sales Order", "store_section", {"label": "Online Store", "fieldtype": "Section Break", "insert_after": "more_info", "collapsible": 1, "depends_on": "store_order"}),
	("Sales Order", "store_order", {"label": "Online Order", "fieldtype": "Check", "insert_after": "store_section", "read_only": 1, "in_standard_filter": 1, "no_copy": 1}),
	("Sales Order", "store_payment_method", {"label": "Payment Method", "fieldtype": "Data", "insert_after": "store_order", "read_only": 1, "no_copy": 1}),
	("Sales Order", "store_payment_status", {"label": "Online Payment", "fieldtype": "Select", "options": "\nUnpaid\nPending\nPaid\nFailed", "insert_after": "store_payment_method", "read_only": 1, "in_standard_filter": 1, "no_copy": 1}),
	("Sales Order", "store_col", {"fieldtype": "Column Break", "insert_after": "store_payment_status"}),
	("Sales Order", "store_phone", {"label": "Customer Phone", "fieldtype": "Data", "insert_after": "store_col", "read_only": 1, "no_copy": 1}),
	("Sales Order", "store_notes", {"label": "Customer Notes", "fieldtype": "Small Text", "insert_after": "store_phone", "read_only": 1, "no_copy": 1}),
	("Sales Order", "store_payment_ref", {"label": "Payment Reference", "fieldtype": "Data", "insert_after": "store_notes", "read_only": 1, "no_copy": 1}),
	("Sales Order", "store_key", {"label": "Tracking Key", "fieldtype": "Data", "insert_after": "store_payment_ref", "read_only": 1, "hidden": 1, "no_copy": 1}),
	("Car", "store_publish", {"label": "Show in the Online Store", "fieldtype": "Check", "insert_after": "status", "in_standard_filter": 1}),
	("Room Type", "store_publish", {"label": "Show in the Online Store", "fieldtype": "Check", "insert_after": "room_type_name", "in_standard_filter": 1}),
]


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True
	return bool(set(frappe.get_roles()) & set(ROLES + ["System Manager", "Sales Manager"]))


def after_install():
	_all()


def after_migrate():
	_all()


def _all():
	for fn in (ensure_module, ensure_roles, ensure_custom_fields, ensure_settings, refresh_workspace):
		try:
			fn()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"ledgerx_store install step failed: {fn.__name__}")
	frappe.clear_cache()


def ensure_module():
	if not frappe.db.exists("Module Def", MODULE):
		frappe.get_doc({"doctype": "Module Def", "module_name": MODULE, "app_name": "ledgerx_store"}).insert(ignore_permissions=True)


def ensure_roles():
	for r in ROLES:
		if not frappe.db.exists("Role", r):
			frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(ignore_permissions=True)


def ensure_custom_fields():
	for dt, name, spec in FIELDS:
		if frappe.db.exists("DocType", dt) and not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": name}):
			frappe.get_doc({"doctype": "Custom Field", "dt": dt, "fieldname": name, **spec}).insert(ignore_permissions=True)


def ensure_settings():
	s = frappe.get_doc("Store Settings")
	changed = False
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
	if not s.company and company:
		s.company, changed = company, True
	if not s.store_name and company:
		s.store_name, changed = frappe.db.get_value("Company", company, "company_name") or company, True
	if not s.price_list:
		pl = "Standard Selling" if frappe.db.exists("Price List", "Standard Selling") else frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
		if pl:
			s.price_list, changed = pl, True
	if changed and s.company and s.store_name and s.price_list:
		s.save(ignore_permissions=True)


def refresh_workspace():
	base = os.path.join(frappe.get_app_path("ledgerx_store"), FOLDER)
	for dt in ("number_card", "dashboard_chart"):
		folder = os.path.join(base, dt)
		for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
			if os.path.isdir(os.path.join(folder, name)):
				frappe.reload_doc(FOLDER, dt, name, force=True)
	frappe.reload_doc(FOLDER, "workspace", "store", force=True)

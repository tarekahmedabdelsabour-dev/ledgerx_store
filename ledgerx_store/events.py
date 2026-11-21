"""Settings and Item events."""
import frappe
from frappe import _

from ledgerx_store.engine import cart


def settings_validate(doc, method=None):
	if doc.online_gateway == "Paymob" and not (doc.paymob_integration_id and doc.paymob_iframe_id and doc.online_mode_of_payment):
		frappe.throw(_("For Paymob fill the integration ID, the frame ID and the mode of payment."))
	if (doc.shipping_fee or 0) > 0 and not doc.shipping_account:
		frappe.throw(_("Set the shipping income account, or make the shipping fee zero."))


def settings_on_update(doc, method=None):
	if doc.make_home_page:
		frappe.db.set_single_value("Website Settings", "home_page", "store")
	elif frappe.db.get_single_value("Website Settings", "home_page") == "store":
		frappe.db.set_single_value("Website Settings", "home_page", "")


def item_validate(doc, method=None):
	if not doc.get("store_publish"):
		return
	taken = set(frappe.get_all("Item", filters={"store_slug": ["is", "set"], "name": ["!=", doc.name]}, pluck="store_slug"))
	if not doc.store_slug:
		doc.store_slug = cart.unique_slug(cart.slugify(doc.item_name or doc.name, doc.name), taken)
	elif doc.store_slug in taken:
		frappe.throw(_("Another product already uses the address part {0}.").format(doc.store_slug))
	if doc.get("ph_is_drug") and not cart.sellable_pharmacy(doc.ph_is_drug, doc.get("ph_class")):
		frappe.throw(_("Prescription and controlled drugs cannot be sold online."))


def group_validate(doc, method=None):
	if doc.get("store_visible") and not doc.store_slug:
		doc.store_slug = cart.slugify(doc.item_group_name or doc.name, doc.name)

"""Calls used by the store pages. Guests may browse, price a cart, order and send requests; everything else needs a login."""
import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from ledgerx_store import data, inquiries, orders


def _json(v, default):
	if isinstance(v, str):
		try:
			return json.loads(v)
		except ValueError:
			return default
	return v if v is not None else default


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)
def quote(lines=None, pickup=0):
	q, _cat = orders.quote(_json(lines, []), bool(int(pickup or 0)))
	return q


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def place_order(lines=None, info=None, address=None, payment="Cash on Delivery", pickup=0):
	s = data.settings()
	if not data.warehouses():
		frappe.throw(_("The store is not ready to take orders yet."))
	info, address = _json(info, {}), _json(address, {})
	so = orders.place(_json(lines, []), info, address, payment, bool(int(pickup or 0)), frappe.session.user)
	res = {"order": so.name, "key": so.store_key, "total": so.grand_total, "payment": payment, "url": f"/order?id={so.name}&k={so.store_key}"}
	if payment == "Online Payment":
		if s.online_gateway == "Paymob":
			from ledgerx_store.gateways import paymob

			try:
				res["pay_url"] = paymob.start(so, info, address)
			except Exception:
				frappe.log_error(title=f"Store: could not start payment for {so.name}")
				res["pay_error"] = _("We could not open the payment page. Your order is saved: pay on the next screen or contact us.")
	return res


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def send_inquiry(kind, full_name, phone="", email="", message="", ref_doctype="", ref_name="", date_from=None, date_to=None, guests=None):
	return inquiries.create(kind, full_name, phone, email, message, ref_doctype, ref_name, date_from, date_to, guests)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def paymob_callback(**kwargs):
	"""Paymob posts the transaction here. The signature in the query string is checked before anything changes."""
	from ledgerx_store.gateways import paymob

	payload = frappe.request.get_json(silent=True) or {}
	try:
		return {"ok": bool(paymob.handle_callback(payload, frappe.form_dict.get("hmac")))}
	except frappe.PermissionError:
		frappe.local.response["http_status_code"] = 403
		return {"ok": False}


@frappe.whitelist(methods=["POST"])
def mark_paid(order, mode_of_payment, reference=None):
	"""Staff button on the Sales Order: the transfer arrived."""
	if not set(frappe.get_roles()) & {"Store Manager", "Accounts Manager", "System Manager"}:
		frappe.throw(_("You are not allowed to do this."), frappe.PermissionError)
	return orders.record_payment(order, mode_of_payment, reference)

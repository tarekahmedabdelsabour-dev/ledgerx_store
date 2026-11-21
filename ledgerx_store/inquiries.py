"""Contact, test-drive and booking requests: a Store Inquiry, a Lead in the CRM, and the showroom's own Test Drive."""
import frappe
from frappe import _

from ledgerx_store.engine import cart

KINDS = ("Contact", "Test Drive", "Car Interest", "Hotel Booking", "Service")


def _lead_source():
	if not frappe.db.exists("Lead Source", "Website"):
		frappe.get_doc({"doctype": "Lead Source", "source_name": "Website"}).insert(ignore_permissions=True)
	return "Website"


def create(kind, full_name, phone, email="", message="", ref_doctype="", ref_name="", date_from=None, date_to=None, guests=None):
	if kind not in KINDS:
		frappe.throw(_("Choose what you need."))
	full_name = (full_name or "").strip()
	if len(full_name) < 2:
		frappe.throw(_("Enter your name."))
	if not cart.valid_phone(phone) and not cart.valid_email(email):
		frappe.throw(_("Enter a phone number or an email address so we can reach you."))
	if email and not cart.valid_email(email):
		frappe.throw(_("The email address is not valid."))
	inq = frappe.get_doc({"doctype": "Store Inquiry", "kind": kind, "full_name": full_name[:140], "phone": (phone or "")[:40], "email": (email or "")[:140], "message": (message or "")[:2000],
		"ref_doctype": ref_doctype if ref_doctype in ("Car", "Room Type", "Item") else "", "ref_name": (ref_name or "")[:140], "date_from": date_from or None, "date_to": date_to or None, "guests": guests or None})
	inq.insert(ignore_permissions=True)
	try:
		lead = _lead_for(inq)
		inq.db_set("lead", lead, update_modified=False)
		if kind == "Test Drive" and inq.ref_doctype == "Car" and frappe.db.exists("DocType", "Test Drive") and frappe.db.exists("Car", inq.ref_name):
			frappe.get_doc({"doctype": "Test Drive", "car": inq.ref_name, "lead_name": inq.full_name, "phone": inq.phone, "drive_date": f"{inq.date_from} 10:00:00" if inq.date_from else None, "outcome": "Scheduled", "notes": inq.message}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Store: inquiry follow-up")
	return inq.name


def _lead_for(inq):
	exist = None
	if inq.email:
		exist = frappe.db.get_value("Lead", {"email_id": inq.email}, "name")
	if not exist and inq.phone:
		exist = frappe.db.get_value("Lead", {"mobile_no": inq.phone}, "name")
	if exist:
		lead = exist
	else:
		first, _s, last = inq.full_name.partition(" ")
		doc = frappe.get_doc({"doctype": "Lead", "first_name": first, "last_name": last, "email_id": inq.email or None, "mobile_no": inq.phone or None, "source": _lead_source()})
		doc.insert(ignore_permissions=True)
		lead = doc.name
	about = f"{inq.kind}" + (f" - {inq.ref_doctype} {inq.ref_name}" if inq.ref_name else "")
	dates = f" ({inq.date_from or ''} {inq.date_to or ''})".replace("( )", "") if (inq.date_from or inq.date_to) else ""
	frappe.get_doc({"doctype": "Comment", "comment_type": "Comment", "reference_doctype": "Lead", "reference_name": lead, "content": f"Website request: {about}{dates}<br>{frappe.utils.escape_html(inq.message or '')}"}).insert(ignore_permissions=True)
	return lead

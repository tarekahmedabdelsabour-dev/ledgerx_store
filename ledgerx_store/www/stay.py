import frappe
from frappe import _

from ledgerx_store import data, web


def get_context(context):
	web.base(context, _("Rooms"))
	context.rooms = data.rooms()
	if not context.rooms:
		raise frappe.DoesNotExistError

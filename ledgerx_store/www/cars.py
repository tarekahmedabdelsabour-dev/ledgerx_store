import frappe
from frappe import _

from ledgerx_store import data, web


def get_context(context):
	web.base(context, _("Cars for sale"))
	context.cars = data.cars()
	if not context.cars:
		raise frappe.DoesNotExistError

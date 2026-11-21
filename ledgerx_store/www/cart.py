from frappe import _

from ledgerx_store import web


def get_context(context):
	web.base(context, _("Cart"))

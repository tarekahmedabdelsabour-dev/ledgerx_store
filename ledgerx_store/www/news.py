from frappe import _

from ledgerx_store import data, web


def get_context(context):
	web.base(context, _("News"))
	context.posts = data.news(30)

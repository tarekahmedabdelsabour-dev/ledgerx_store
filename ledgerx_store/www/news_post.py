import frappe

from ledgerx_store import web


def get_context(context):
	name = frappe.form_dict.get("slug")
	post = frappe.db.get_value("Blog Post", {"name": name, "published": 1}, ["name", "title", "blog_intro", "meta_image", "published_on", "content_type", "content", "content_html", "content_md"], as_dict=True) if name else None
	if not post:
		raise frappe.DoesNotExistError
	web.base(context, post.title, post.blog_intro, post.meta_image)
	context.post = post
	if post.content_type == "Markdown":
		context.body = frappe.utils.md_to_html(post.content_md or "")
	elif post.content_type == "HTML":
		context.body = post.content_html or ""
	else:
		context.body = post.content or ""

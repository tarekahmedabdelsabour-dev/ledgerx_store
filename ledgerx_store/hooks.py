app_name = "ledgerx_store"
app_title = "Store"
app_publisher = "LedgerX"
app_description = "Online store and website connected to stock, pricing, CRM, pharmacy, showroom and hotels"
app_email = "hello@ledgerx.local"
app_license = "mit"

required_apps = ["erpnext"]

add_to_apps_screen = [
	{
		"name": "ledgerx_store",
		"logo": "/assets/ledgerx_store/images/store.svg",
		"title": "Store",
		"route": "/desk/store",
		"has_permission": "ledgerx_store.install.check_app_permission",
	}
]

website_route_rules = [
	{"from_route": "/product/<path:slug>", "to_route": "product"},
	{"from_route": "/p/<path:slug>", "to_route": "page"},
	{"from_route": "/news/<path:slug>", "to_route": "news_post"},
	{"from_route": "/car/<path:slug>", "to_route": "car"},
]

doc_events = {
	"Store Settings": {"validate": "ledgerx_store.events.settings_validate", "on_update": "ledgerx_store.events.settings_on_update"},
	"Item": {"validate": "ledgerx_store.events.item_validate"},
	"Item Group": {"validate": "ledgerx_store.events.group_validate"},
}

scheduler_events = {"hourly": ["ledgerx_store.tasks.hourly"]}

from ledgerx_store import __version__ as _v  # noqa: E402

app_include_js = [f"/assets/ledgerx_store/js/store_forms.js?v={_v}"]

after_install = "ledgerx_store.install.after_install"
after_migrate = "ledgerx_store.install.after_migrate"

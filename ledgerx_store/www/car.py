import frappe

from ledgerx_store import data, web


def get_context(context):
	name = frappe.form_dict.get("slug")
	car = frappe.db.get_value("Car", {"name": name, "store_publish": 1, "status": "Ready for Sale"}, ["name", "make", "model", "year", "mileage", "color", "fuel", "transmission", "engine_cc", "condition", "asking_price", "image", "notes"], as_dict=True) if data.cars(1) else None
	if not car:
		raise frappe.DoesNotExistError
	web.base(context, f"{car.make} {car.model} {car.year or ''}".strip(), None, car.image)
	context.car = car

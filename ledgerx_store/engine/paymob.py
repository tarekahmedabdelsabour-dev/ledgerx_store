"""Paymob Accept: request bodies and callback signature check, no network here.
Flow: auth token -> order -> payment key -> iframe. The callback carries an HMAC (SHA-512) of selected fields."""
import hashlib
import hmac

HMAC_FIELDS = [
	"amount_cents", "created_at", "currency", "error_occured", "has_parent_transaction", "id", "integration_id", "is_3d_secure",
	"is_auth", "is_capture", "is_refunded", "is_standalone_payment", "is_voided", "order.id", "owner", "pending",
	"source_data.pan", "source_data.sub_type", "source_data.type", "success",
]


def _dig(obj, path):
	cur = obj
	for p in path.split("."):
		cur = cur.get(p) if isinstance(cur, dict) else None
	return cur


def _txt(v):
	if isinstance(v, bool):
		return "true" if v else "false"
	return "" if v is None else str(v)


def hmac_message(obj):
	return "".join(_txt(_dig(obj, f)) for f in HMAC_FIELDS)


def sign(obj, secret):
	return hmac.new(secret.encode(), hmac_message(obj).encode(), hashlib.sha512).hexdigest()


def verify(obj, received, secret):
	return bool(secret and received) and hmac.compare_digest(sign(obj, secret), str(received).lower())


def cents(amount):
	return int(round(float(amount) * 100))


def billing(name, email, phone, address):
	first, _, last = (name or "Customer").strip().partition(" ")
	return {"first_name": first or "Customer", "last_name": last or "NA", "email": email or "NA", "phone_number": phone or "NA",
		"apartment": "NA", "floor": "NA", "building": "NA", "street": (address or {}).get("line1") or "NA", "city": (address or {}).get("city") or "NA",
		"state": (address or {}).get("state") or "NA", "country": (address or {}).get("country") or "EG", "postal_code": "NA", "shipping_method": "NA"}


def iframe_url(iframe_id, payment_token):
	return f"https://accept.paymob.com/api/acceptance/iframes/{iframe_id}?payment_token={payment_token}"

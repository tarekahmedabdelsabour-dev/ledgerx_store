"""Pure store rules: slugs, cart pricing, shipping, tax, order totals. No database."""
import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal


def d(x):
	return Decimal(str(x or 0))


def r2(x):
	return float(d(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def slugify(text, fallback="item"):
	"""Keeps letters of any script (Arabic included), turns everything else into single dashes."""
	t = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
	t = re.sub(r"[ً-ٰٟـ]", "", t)  # Arabic marks and tatweel
	t = re.sub(r"[^\w]+", "-", t, flags=re.UNICODE).strip("-_")
	return t[:80] or fallback


def unique_slug(base, taken):
	s, i = base, 2
	while s in taken:
		s = f"{base}-{i}"
		i += 1
	return s


def clean_qty(raw, max_qty=None, step=1):
	"""Whole number >= 1, optionally capped. Returns 0 for junk."""
	try:
		q = int(float(raw))
	except (TypeError, ValueError):
		return 0
	if q < 1:
		return 0
	if max_qty is not None:
		q = min(q, int(max_qty))
	return q


def shipping_fee(subtotal, fee, free_over, pickup=False):
	if pickup or not fee:
		return 0.0
	if free_over and d(subtotal) >= d(free_over):
		return 0.0
	return r2(fee)


def price_cart(lines, catalog, tax_rate=0.0, fee=0.0, free_over=0.0, min_order=0.0, pickup=False):
	"""lines: [{item, qty}]; catalog: {item: {price, stock, max_qty, name, backorder, sellable}}.
	Returns dict(lines, subtotal, tax, shipping, total, problems). A line that cannot be sold is dropped and explained."""
	out, problems, merged = [], [], {}
	for ln in lines or []:
		code = (ln or {}).get("item")
		qty = clean_qty((ln or {}).get("qty"))
		if code and qty:
			merged[code] = merged.get(code, 0) + qty
	sub = d(0)
	for code, qty in merged.items():
		it = catalog.get(code)
		if not it or not it.get("sellable", True) or not it.get("price"):
			problems.append({"item": code, "code": "unavailable"})
			continue
		cap = it.get("max_qty")
		avail = None if (it.get("backorder") or it.get("stock") is None) else max(0, int(it["stock"]))
		allowed = min([x for x in (cap, avail) if x is not None], default=None)
		if allowed is not None and allowed <= 0:
			problems.append({"item": code, "code": "out_of_stock", "name": it.get("name")})
			continue
		if allowed is not None and qty > allowed:
			problems.append({"item": code, "code": "reduced", "name": it.get("name"), "to": allowed})
			qty = allowed
		amount = d(it["price"]) * qty
		sub += amount
		out.append({"item": code, "name": it.get("name"), "qty": qty, "price": r2(it["price"]), "amount": r2(amount), "image": it.get("image"), "max": allowed})
	tax = d(r2(sub * d(tax_rate) / 100))
	ship = d(shipping_fee(sub, fee, free_over, pickup)) if out else d(0)
	res = {"lines": out, "subtotal": r2(sub), "tax": float(tax), "shipping": float(ship), "total": r2(sub + tax + ship), "problems": problems}
	if min_order and out and sub < d(min_order):
		res["problems"].append({"code": "below_minimum", "minimum": r2(min_order)})
	return res


def sellable_pharmacy(ph_is_drug, ph_class):
	"""Prescription and controlled drugs are never sold online."""
	if not ph_is_drug:
		return True
	return (ph_class or "") in ("OTC", "Cosmetic", "Supplement", "Medical Supply")


def valid_phone(p):
	digits = re.sub(r"\D", "", str(p or ""))
	return 8 <= len(digits) <= 15


def valid_email(e):
	return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(e or "")))

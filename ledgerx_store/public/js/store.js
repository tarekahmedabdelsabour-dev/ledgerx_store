(function () {
	"use strict";
	const T = (k, ...a) => { let s = (window.LX_I18N && window.LX_I18N[k]) || k; a.forEach((v, i) => (s = s.replace("{" + i + "}", v))); return s; };
	const root = () => document.getElementById("lx-main");
	const cur = () => (root() && root().dataset.currency) || "EGP";
	const loc = () => ((root() && root().dataset.lang) || "ar") === "ar" ? "ar-EG" : (root().dataset.lang || "en");
	const money = (v) => { try { return new Intl.NumberFormat(loc(), { style: "currency", currency: cur() }).format(v); } catch (e) { return Number(v).toFixed(2) + " " + cur(); } };
	const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

	let mem = {};
	const store = {
		get() { try { return JSON.parse(localStorage.getItem("lx_cart") || "{}") || {}; } catch (e) { return mem; } },
		set(c) { mem = c; try { localStorage.setItem("lx_cart", JSON.stringify(c)); } catch (e) { /* private mode: memory only */ } badge(); },
	};
	const lines = () => Object.entries(store.get()).map(([item, qty]) => ({ item, qty }));
	function badge() {
		const n = Object.values(store.get()).reduce((a, b) => a + (+b || 0), 0);
		document.querySelectorAll("[data-cart-count]").forEach((e) => { e.textContent = n; e.hidden = !n; });
	}
	function toast(msg) {
		const t = document.createElement("div");
		t.className = "lx-toast"; t.setAttribute("role", "status"); t.textContent = msg;
		document.body.appendChild(t); setTimeout(() => t.remove(), 2600);
	}
	function call(method, args, ok, bad) {
		frappe.call({ method: "ledgerx_store.api." + method, type: "POST", args, callback: (r) => ok && ok(r.message), error: () => bad && bad() });
	}
	function errText(xhr) {
		try { const m = JSON.parse(JSON.parse(xhr.responseText)._server_messages)[0]; return JSON.parse(m).message.replace(/<[^>]+>/g, ""); } catch (e) { return T("Something went wrong. Try again."); }
	}
	function api(method, args) {
		return new Promise((res, rej) => frappe.call({ method: "ledgerx_store.api." + method, type: "POST", args, callback: (r) => res(r.message), error: (x) => rej(x) }));
	}

	// add to cart
	function bindAdd() {
		document.querySelectorAll("[data-add]").forEach((b) => b.addEventListener("click", () => {
			const code = b.dataset.add;
			const qi = document.querySelector('[data-qty-for="' + code + '"]');
			const q = Math.max(1, parseInt(qi ? qi.value : 1, 10) || 1);
			const c = store.get(); c[code] = (+c[code] || 0) + q; store.set(c);
			toast(T("Added to the cart"));
		}));
		document.querySelectorAll(".lx-qty").forEach((w) => {
			const i = w.querySelector("input");
			w.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { i.value = Math.max(1, (parseInt(i.value, 10) || 1) + (b.dataset.step === "+" ? 1 : -1)); }));
		});
	}

	// cart page
	function renderCart(q, box, onChange) {
		const notes = q.problems.map((p) => {
			if (p.code === "out_of_stock" || p.code === "unavailable") return T("No longer available") + (p.name ? ": " + esc(p.name) : "");
			if (p.code === "reduced") return T("The quantity was reduced to {0}", p.to) + ": " + esc(p.name);
			if (p.code === "below_minimum") return T("Minimum order is {0}", money(p.minimum));
			return "";
		}).filter(Boolean).map((t) => '<div class="lx-alert warn">' + t + "</div>").join("");
		if (!q.lines.length) { box.innerHTML = notes + '<div class="lx-empty">' + esc(T("Your cart is empty")) + '<p><a class="lx-btn" href="/shop">' + esc(T("Continue shopping")) + "</a></p></div>"; return; }
		const rows = q.lines.map((l) => '<div class="lx-line"><' + (l.image ? 'img src="' + esc(l.image) + '" alt=""' : "i") + '><div><b>' + esc(l.name) + '</b><div class="lx-muted">' + money(l.price) + '</div><button class="rm" data-rm="' + esc(l.item) + '">' + esc(T("Remove")) + '</button></div><div class="end"><div class="lx-qty"><button type="button" data-d="' + esc(l.item) + '" data-s="-">−</button><input aria-label="qty" value="' + l.qty + '" data-q="' + esc(l.item) + '" inputmode="numeric"><button type="button" data-d="' + esc(l.item) + '" data-s="+">+</button></div><div><b>' + money(l.amount) + "</b></div></div></div>").join("");
		box.innerHTML = notes + '<div class="lx-panel">' + rows + "</div>";
		box.querySelectorAll("[data-rm]").forEach((b) => b.addEventListener("click", () => { const c = store.get(); delete c[b.dataset.rm]; store.set(c); onChange(); }));
		box.querySelectorAll("[data-d]").forEach((b) => b.addEventListener("click", () => { const c = store.get(); c[b.dataset.d] = Math.max(1, (+c[b.dataset.d] || 1) + (b.dataset.s === "+" ? 1 : -1)); store.set(c); onChange(); }));
		box.querySelectorAll("[data-q]").forEach((i) => i.addEventListener("change", () => { const c = store.get(); c[i.dataset.q] = Math.max(1, parseInt(i.value, 10) || 1); store.set(c); onChange(); }));
	}
	function summary(q) {
		return '<div class="lx-sum"><div><span>' + esc(T("Subtotal")) + "</span><span>" + money(q.subtotal) + "</span></div>" +
			(q.tax ? "<div><span>" + esc(T("Tax")) + "</span><span>" + money(q.tax) + "</span></div>" : "") +
			"<div><span>" + esc(T("Shipping")) + "</span><span>" + (q.shipping ? money(q.shipping) : esc(T("Free"))) + '</span></div><div class="total"><span>' + esc(T("Total")) + "</span><span>" + money(q.total) + "</span></div></div>";
	}
	function cartPage() {
		const box = document.getElementById("lx-cart-lines"), sum = document.getElementById("lx-cart-sum");
		if (!box) return;
		const go = () => {
			const l = lines();
			if (!l.length) { renderCart({ lines: [], problems: [] }, box, go); sum.innerHTML = ""; return; }
			api("quote", { lines: JSON.stringify(l) }).then((q) => {
				const c = {}; q.lines.forEach((x) => (c[x.item] = x.qty)); store.set(c);
				renderCart(q, box, go);
				sum.innerHTML = q.lines.length ? summary(q) + '<p><a class="lx-btn accent" style="inline-size:100%" href="/checkout">' + esc(T("Checkout")) + "</a></p>" : "";
			}).catch(() => { box.innerHTML = '<div class="lx-alert">' + esc(T("Something went wrong. Try again.")) + "</div>"; });
		};
		go();
	}

	// checkout
	function checkoutPage() {
		const form = document.getElementById("lx-checkout");
		if (!form) return;
		const sum = document.getElementById("lx-co-sum"), err = document.getElementById("lx-co-err"), btn = form.querySelector("[type=submit]");
		const pickup = () => form.elements.pickup && form.elements.pickup.checked;
		const refresh = () => {
			document.getElementById("lx-addr").hidden = !!pickup();
			if (!lines().length) { location.href = "/cart"; return; }
			api("quote", { lines: JSON.stringify(lines()), pickup: pickup() ? 1 : 0 }).then((q) => {
				const c = {}; q.lines.forEach((x) => (c[x.item] = x.qty)); store.set(c);
				sum.innerHTML = q.lines.map((l) => '<div class="lx-line" style="grid-template-columns:minmax(0,1fr) auto"><span>' + esc(l.name) + " × " + l.qty + "</span><b>" + money(l.amount) + "</b></div>").join("") + summary(q);
				btn.disabled = !q.lines.length || q.problems.some((p) => p.code === "below_minimum");
			});
		};
		if (form.elements.pickup) form.elements.pickup.addEventListener("change", refresh);
		refresh();
		form.addEventListener("submit", (e) => {
			e.preventDefault(); err.hidden = true; btn.disabled = true; const label = btn.textContent; btn.textContent = T("Placing your order");
			const f = new FormData(form);
			api("place_order", {
				lines: JSON.stringify(lines()), pickup: pickup() ? 1 : 0, payment: f.get("payment") || "Cash on Delivery",
				info: JSON.stringify({ name: f.get("name"), phone: f.get("phone"), email: f.get("email"), notes: f.get("notes") }),
				address: JSON.stringify({ line1: f.get("line1"), line2: f.get("line2"), city: f.get("city"), state: f.get("state") }),
			}).then((r) => { store.set({}); location.href = r.pay_url || r.url; })
				.catch((x) => { err.textContent = errText(x); err.hidden = false; btn.disabled = false; btn.textContent = label; });
		});
	}

	// requests (contact, test drive, booking)
	function inquiryForms() {
		document.querySelectorAll("form[data-inquiry]").forEach((form) => form.addEventListener("submit", (e) => {
			e.preventDefault();
			const ok = form.querySelector("[data-ok]"), er = form.querySelector("[data-err]"), b = form.querySelector("[type=submit]");
			er.hidden = true; ok.hidden = true; b.disabled = true;
			const f = new FormData(form), a = { kind: form.dataset.inquiry };
			f.forEach((v, k) => (a[k] = v));
			if (form.dataset.refDoctype) { a.ref_doctype = form.dataset.refDoctype; a.ref_name = form.dataset.refName; }
			api("send_inquiry", a).then(() => { form.reset(); ok.hidden = false; b.disabled = false; })
				.catch((x) => { er.textContent = errText(x); er.hidden = false; b.disabled = false; });
		}));
	}

	function init() { badge(); bindAdd(); cartPage(); checkoutPage(); inquiryForms(); }
	window.addEventListener("load", () => { if (window.frappe && frappe.call) init(); else { badge(); bindAdd(); } });
	window.LX = { store, money };
})();

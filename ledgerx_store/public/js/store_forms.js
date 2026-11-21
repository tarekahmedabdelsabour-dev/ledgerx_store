(function () {
	frappe.ui.form.on("Sales Order", {
		refresh(frm) {
			const d = frm.doc;
			if (!d.store_order || d.docstatus !== 1 || d.store_payment_status === "Paid") return;
			frm.add_custom_button(__("Record Payment"), () => {
				frappe.prompt([
					{ fieldname: "mode_of_payment", label: __("Mode of Payment"), fieldtype: "Link", options: "Mode of Payment", reqd: 1 },
					{ fieldname: "reference", label: __("Reference"), fieldtype: "Data" },
				], (v) => frappe.call({ method: "ledgerx_store.api.mark_paid", args: { order: d.name, mode_of_payment: v.mode_of_payment, reference: v.reference }, freeze: true, callback: () => frm.reload_doc() }), __("The payment arrived"));
			}, __("Store"));
		},
	});
})();

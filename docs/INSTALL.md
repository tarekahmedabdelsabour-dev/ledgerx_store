# Install

```bash
cd ~/frappe-bench-v16
git clone <repo-url> apps/ledgerx_store
printf '\nledgerx_store\n' >> sites/apps.txt
./env/bin/pip install -e apps/ledgerx_store
ln -sfn ~/frappe-bench-v16/apps/ledgerx_store/ledgerx_store/public sites/assets/ledgerx_store
bench --site mysite.localhost install-app ledgerx_store
bench --site mysite.localhost migrate
bench --site mysite.localhost clear-cache
```
Full restart, then Ctrl+Shift+R. Open the store at `http://mysite.localhost:8001/store`.

## First day
1. **Store Settings**: name, company, price list, the warehouse(s) that fill online orders, shipping fee (and the shipping income account), payment methods, contact details.
2. **Item Group**: tick *Show in the Online Store* on the categories you want.
3. **Item**: tick *Show in the Online Store* on each product. It needs a price in the store price list, an image, and stock in the chosen warehouse (or tick *Sell even when out of stock*).
4. Open `/store`. Add to cart, check out as a guest, and look at the Sales Order that was created.
5. Open `/contact-us` and send a message: a Lead and a Store Inquiry appear.

## Pharmacy, cars, hotels
- Pharmacy products appear when their class is OTC, Cosmetic, Supplement or Medical Supply. Prescription and controlled products are blocked even if someone ticks the box. Expired batches are not counted in the stock the store shows.
- Cars: tick *Show Cars for Sale* in Store Settings and *Show in the Online Store* on each Car (status Ready for Sale). A test-drive request creates a Test Drive and a Lead.
- Rooms: tick *Show Hotel Rooms* and *Show in the Online Store* on each Room Type. The price shown is the lowest public rate plan. A request creates a Store Inquiry and a Lead; availability is confirmed by your team.

## Payment
- **Bank transfer or wallet**: the customer sees your instructions. When the money arrives press **Store > Record Payment** on the Sales Order.
- **Paymob**: in Paymob's dashboard create a card integration and a frame. Put the API key, integration ID, frame ID and HMAC secret in Store Settings, choose the Mode of Payment that should receive the money, and give Paymob this *transaction processed callback* address:
  `https://<your-site>/api/method/ledgerx_store.api.paymob_callback`
  and set the redirect address after payment to `https://<your-site>/store`. The order is marked paid only when the signed callback arrives and the amount matches.
- Online orders left unpaid for 24 hours are marked *Failed* so your team can call or cancel them.

## Make it the home page
Tick *Use the Store as the Home Page of the Website* in Store Settings.

## Not included yet
Discount codes and pricing rules, product variants and extra photos, delivery zones with different fees, customer reviews, wishlist, and automatic batch picking at delivery for pharmacy items (use the usual Delivery Note).

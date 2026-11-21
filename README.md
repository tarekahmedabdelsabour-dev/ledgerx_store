# LedgerX Store

An online store and a website, connected to the same stock, prices, customers, orders, invoices and CRM as the rest of LedgerX.

- **Store**: product list with search, categories and sorting; product page; cart in the browser; checkout for guests and signed-in customers; order status page and "My orders".
- **Orders**: every web order is a normal Sales Order (customer, address and contact are created or reused). Stock, delivery notes, invoices and payments follow the usual flow.
- **Payment**: cash on delivery; bank transfer or wallet confirmed by staff with one button (it creates the Payment Entry); online card payment through Paymob.
- **Pages**: pages you write yourself, news from the blog, a contact form that creates a Lead in the CRM, and a "My orders" page.
- **Other modules**: over-the-counter pharmacy products (prescription and controlled drugs are never sold), cars for sale with a test-drive request (creates the showroom's Test Drive), hotel rooms with a booking request.
- Arabic first (right-to-left), works in English too. No page needs the desk.

## Status: read this first
The pricing, stock, tax, shipping rules, slugs and the Paymob signature check are unit tested (15 tests) and all 14 page templates render with test data. **The database code and the pages have not been run on a live site**, and no payment gateway account was available: test everything on a copy with test orders, and use Paymob's test mode first.

See `docs/INSTALL.md`.

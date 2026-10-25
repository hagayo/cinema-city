# Paddle Sandbox checkout smoke test

This first phase creates a **one-time test transaction** through the Python server,
opens Paddle.js checkout, and reads the resulting transaction status from Paddle.
It does not create cinema bookings, reserve seats, grant access, create subscriptions,
or receive webhooks. Existing cinema booking behavior is unchanged.

## Sandbox resources created for this project

On 2026-10-25 the approved test catalog was created and read back from Paddle:

- Product: `pro_01m5s5eqpg8x2k5kdcahr1kdyv` — Cinema City Sandbox Test, category `standard`.
- Price: `pri_01m5s5eqwkn88m5rz5j4t4z7p0` — USD 1.00 base price, quantity exactly 1,
  active, one-time, no trial. The ID is saved in `.env.development`.
- A sandbox client token was created and saved privately in `.env.development`.

The initial real sandbox transaction request returned
`transaction_default_checkout_url_not_set`. The account needs its Default payment
link configured before an end-to-end checkout can succeed. The current API key
returned `403 forbidden` when reading `/settings/checkout-url`; use the sandbox
dashboard or grant the appropriate checkout settings permissions.

## Configuration

In `.env.development`:

```dotenv
BILLING_PROVIDER=paddle
PADDLE_ENV=sandbox
PADDLE_API_KEY=your_sandbox_api_key
PADDLE_CLIENT_TOKEN=your_test_client_token
PADDLE_TEST_PRICE_ID=your_one_time_sandbox_price_id
PADDLE_WEBHOOK_SECRET=
```

- The API key must start with `pdl_sdbx_apikey_`. Keep it server-side and out of Git.
- The client-side token must start with `test_`. It is intentionally public to Paddle.js.
- Use an **active, one-time** sandbox price (`pri_...`), without a trial. The server
  checks this before every transaction and fixes quantity to 1. It never accepts a
  price, amount, or user ID from the browser.
- API permissions needed at runtime: `price.read`, `transaction.write`, `transaction.read`.
- Bootstrap permissions, only if creating account resources via API:
  `product.read`, `product.write`, `price.write`, `client_token.read`, `client_token.write`.
- Set the sandbox **Default payment link** in Paddle Checkout configuration to a
  suitable page on your own domain that loads Paddle.js. Sandbox checkout itself can
  be opened on localhost. Reading this setting via API requires `checkout_settings.read`.
- `PADDLE_WEBHOOK_SECRET` is reserved for phase two and may remain empty.
- Monthly, annual and trial price variables from the other project are unused.
- `BILLING_PROVIDER=disabled` (default) or the legacy `fake` value disables all payment
  routes. `fake` is accepted for configuration compatibility; no fake payment is simulated.
- Enabling Paddle with missing/invalid configuration fails startup. Production app
  environments and live Paddle credentials are rejected. API requests always target
  `https://sandbox-api.paddle.com`, with redirects disabled.

Select the profile **before** starting the process, in PowerShell:

```powershell
$env:APP_ENV = "development"
uv run cinema-web
```

Putting `APP_ENV` inside `.env.development` does not select that file. The loader
first reads the process environment (default `local`), then `.env` and the selected
profile. Existing process environment variables override dotenv values.

Open [the test page](http://127.0.0.1:8000/sandbox-payment). Sign in using the existing
Clerk flow if authentication is enabled. In local NoAuth mode the existing local
customer identity is used. The page and endpoints are available only on the customer
or combined gateway when Paddle is enabled.

## Manual end-to-end check

### Public payment-link page on Render

The public page `/paddle-payment` only initializes Sandbox Paddle.js with the public
client token. It opens transactions through Paddle's `_ptxn` query parameter; it
does not create transactions, use an API key, require Clerk login, or confirm bookings.
It can be served with `APP_ENV=production` while the local test API remains disabled.

After deploying this code to the intended Render service, set these service environment
variables (keep the existing authentication, storage, host and other settings):

```dotenv
APP_ENV=production
BILLING_PROVIDER=disabled
PADDLE_PAYMENT_LINK_ENABLED=true
PADDLE_ENV=sandbox
PADDLE_CLIENT_TOKEN=your_test_client_token_from_the_same_sandbox_account
```

No Paddle API key, price ID or webhook secret is needed on Render for this page.
Keep the local development environment configured with `BILLING_PROVIDER=paddle`.
Render does not obtain secrets from the ignored local `.env.development` file.

Verify `https://cinema-city.onrender.com/paddle-payment` loads the Sandbox-ready
message, then set that exact URL under **Paddle Sandbox → Checkout → Checkout
configuration → Default payment link**. The page must be deployed before using it.
The hostname must be permitted by the service's existing `ALLOWED_HOSTS` setting.
Sandbox does not require website approval for the default link.

The default link is account-wide. A new API key in the same account does not isolate
this setting from the other project. Choose the intended Sandbox account first.

### Local test flow

1. Click **פתיחת תשלום בדיקה**. Confirm the overlay displays **Test Mode**, the
   expected sandbox product, amount and currency.
2. Use test card `4242 4242 4242 4242`, any future expiry and a three-digit CVC.
   Enter test customer details; never use a real card.
3. Complete checkout. The browser completion event triggers a server status check.
   Only Paddle API status `completed` produces the server-confirmed success message.
   If processing is still in progress, click **בדיקת סטטוס ב־Paddle** again.
4. Confirm the transaction ID appears in the sandbox dashboard and that cinema
   bookings and seat availability are unchanged.
5. To test rejection, use `4000 0000 0000 0002`. Close/reopen the overlay to verify
   that an unfinished transaction is reused. Its ID is retained for this browser tab.

The API status check is for this smoke test only. Phase two must persist payment
state and verify signed webhooks for durable booking confirmation.

## Troubleshooting

- Startup rejects missing settings: fill the sandbox values or disable billing.
- Checkout won't open: check the client token belongs to the same sandbox account,
  the configured price is active, and Default payment link is set.
- API failure: check key permissions and expiry in the sandbox dashboard. Provider
  responses and credentials are deliberately excluded from browser error messages.
- 401: sign in. 403 on status lookup: the transaction does not belong to the current
  local user/test purpose. Use a new browser tab after changing user accounts.
- Real-time completion remains unverified until an actual sandbox checkout succeeds;
  passing mocked tests alone does not establish account readiness.

References: [Sandbox](https://developer.paddle.com/sdks/sandbox/),
[transaction API](https://developer.paddle.com/api-reference/transactions/create-transaction/),
[Paddle.js checkout](https://developer.paddle.com/paddle-js/methods/paddle-checkout-open/).

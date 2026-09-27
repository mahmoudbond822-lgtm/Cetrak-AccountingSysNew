# AUD-014 — Login & Refresh Throttling (Implementation Report)

## 1. Objective

Close AUD-014 (P2, production hardening): the API relied only on DRF's global
`AnonRateThrottle` (20/hour) and `UserRateThrottle` (100/hour), which bound total
API abuse but knew nothing about authentication. Concretely there was:

* no failed-credential accounting on `POST /api/v1/auth/login/`, so passwords
  could be guessed at the global anon ceiling,
* no lock-out or delay of any kind, and
* no endpoint-specific ceiling on `POST /api/v1/auth/refresh/`, so a stolen
  refresh token could be rotated in a loop indefinitely (each rotation writes a
  `BlacklistedToken` row and mints a new pair).

This report covers the implementation, the reasoning behind every limit, the
verification actually run, and what remains unproven.

## 2. Current-HEAD Verification

Work started from a clean tree on branch `014-auto-customer-code` at
`2b08f5a29d2d029728a2cdd47c1e4860eb25b472`
(*feat(tenancy): align tenant columns and decimal balance enforcement*). No other
stream's work is touched: no accounting, tenant, permission, API-contract or
frontend-design-system change is included.

## 3. Historical Findings

`docs/audits/AUD-003-final-production-readiness-reaudit.md` records AUD-014 as
still open and describes the same gap ("global-only throttling ... no
login-specific rate limiting, no lock-out"). `specs/001-project-foundation/tasks.md`
line 178 (T078) is the original unchecked requirement: *"add rate limiting to
login and password reset"*. There is no password-reset endpoint in this codebase,
so login and refresh are the whole of the requirement in practice.

Re-derived from the current code before designing anything:

| Finding | Consequence |
| --- | --- |
| `LOGIN_IP_RATE`/`LOGIN_ACCOUNT_*` did not exist | no credential-level control at all |
| `AuthService.login` returned a failure without recording it | nothing to throttle on |
| refresh accepted unbounded calls per token | unbounded rotation + blacklist writes |
| `prod.py` inherited Django's default LocMemCache | any counter would have been per worker, multiplied by gunicorn workers |
| `SimpleJWT` rotates refresh tokens (`ROTATE_REFRESH_TOKENS = True`) | a per-`jti` budget would reset itself for free |

## 4. Threat model and the two layers

Each endpoint gets two *independent* layers, because each defeats a different
evasion:

1. **Per client address** (`LoginAddressThrottle`, `RefreshAddressThrottle`) —
   bounds the total work one client can force the server to do: bcrypt password
   verification, JWT parsing, signature checks, DB reads and blacklisted-token
   writes. It is a resource brake, and it counts *every* request, successes
   included.
2. **Per principal** (`LoginAccountThrottle`, `RefreshSubjectThrottle`) — shaped
   like the actual attack. A distributed attack rotates its source address, so an
   address-only ceiling resets itself; the account budget on login and the token
   subject budget on refresh do not move when the address does.

DRF's global throttles are untouched and still apply as the outer bound.

## 5. What changed (backend)

### `apps/accounts/throttling.py` (new, 191 lines)

* `throttle_enabled()` — the single `AUTH_THROTTLE.ENABLED` switch.
* `client_ident(request)` — `X-Forwarded-For` (left-most entry) only when the
  deployment declares the proxy trustworthy, otherwise `REMOTE_ADDR`, otherwise
  `"unknown"`.
* `_submitted_email(request)` — normalised address from the login body; a
  malformed body falls through to the serializer's own 400.
* `_verified_refresh_subject(request)` — verifies the refresh token's signature
  *before* trusting its `user_id` claim, falling back to the address when the
  token is absent or invalid.
* `_AddressThrottle(SimpleRateThrottle)` — resolves its rate from settings per
  instance (so tests can override it), keyed by scope + client address.
* `LoginAccountThrottle(BaseThrottle)` — reads the failure budget, refuses
  before the view body runs, and implements `wait()` so DRF emits `Retry-After`.

### `apps/accounts/services.py`

`LoginAttemptService` (~145 lines, `services.py:32`) owns the counting rules; the
throttle class only converts a verdict into a 429. `AuthService.login` now records
a failure for an unknown user and for a wrong password, and clears the budget on
success.

### `apps/accounts/views.py`

```python
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginAddressThrottle, LoginAccountThrottle])
def login_view(request): ...

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([RefreshAddressThrottle, RefreshSubjectThrottle])
def refresh_view(request): ...
```

No other view, payload, serializer or response contract changed. Login still
answers `401 "Invalid email or password."` and refresh still answers `401
"Invalid or expired refresh token."`; a throttled attempt answers DRF's standard
`429 {"detail": "Request was throttled. ..."}` on both.

## 6. Keying, privacy and enumeration

* The account key is `salted_hmac("apps.accounts.login", normalized_email)` — an
  opaque keyed digest. Neither the address, a password, nor a token is ever
  written to the cache or to a log line (asserted by a test that scans the raw
  cache).
* **Existence-agnostic by construction.** A failure is recorded for an address
  that does not exist exactly as for a wrong password, so the *same* generic 429
  with the *same* body is returned for a real account, an unknown address and an
  address nobody has ever used. There is nothing to enumerate.
* Logs are one `WARNING` per account per window ("Login failure budget
  exhausted", keyed identifier, failure count, window) plus `DEBUG` per refused
  attempt with address and path. A sustained attack cannot flood the log volume,
  and no log line identifies a person.

## 7. The lock-out is bounded in time (deliberate design point)

A naive counter re-arms its TTL on every increment, which lets an attacker hold
an account blocked for as long as they keep hammering it — a self-inflicted
denial of service against a known victim. Here the window TTL is written **once**,
by the first failure; every later failure only `incr`s. So:

* the block always ends within `LOGIN_ACCOUNT_WINDOW_SECONDS` of the *first*
  failure, and
* a successful login deletes the state, so the account works the moment its
  owner proves possession of the password.

This relies on the cache preserving an existing TTL across `incr`, which is true
of both LocMem and Redis and is why the opt-in Redis test exists (§12).

## 8. Cache choice, and failing open on purpose

Production now points the cache at Redis when `REDIS_URL` is set — the same
convention Celery already uses (database 1 for the cache, database 0 for the
broker) — because gunicorn runs several workers and the service is expected to
scale out. With a missing `REDIS_URL`, production does **not** silently pretend:
it falls back to LocMemCache and logs a `WARNING` at boot saying the limits are
process-local and multiplied by the worker count.

Cache errors **fail open**. If Redis is unreachable, refusing requests would turn
an infrastructure outage into a lock-out of every user — the exact outcome this
control exists to prevent. The degradation is logged once per process at
`WARNING` (subsequently at `DEBUG` with `exc_info`) so an operator still sees it.

## 9. Proxy trust

`X-Forwarded-For` is client-controlled. It is ignored by default and honoured only
where the deployment says a trusted proxy overwrites it: `prod.py` sets
`TRUST_X_FORWARDED_FOR = True` because the web service is only reachable through
the platform's edge proxy, which rewrites the header. The `docker compose` setup
publishes the service directly and inherits the default, so a forged header buys
an attacker nothing there. Both directions are tested.

## 10. What changed (frontend)

`frontend/src/services/api.js` only: a `429` from the refresh endpoint is treated
as transient. `requestRefresh()` is extracted and, on a `429` carrying
`Retry-After`, the request is retried **once** after at most
`REFRESH_RETRY_MAX_WAIT_SECONDS = 10`. The retry happens inside the existing
`refreshPromise`, so single-flight behaviour is preserved and concurrent 401s
still cannot fan out into several refresh calls. No UI, route, payload or session
storage change; `LoginPage` already renders `data.detail`, so a throttled login
shows the server's message.

## 11. Configuration

`settings.AUTH_THROTTLE` in `base.py` (no secrets, so not environment-driven):

| Key | Value | Why this number |
| --- | --- | --- |
| `ENABLED` | `True` (`False` in test settings) | suite keeps its previous behaviour; the dedicated tests re-enable it |
| `LOGIN_IP_RATE` | `20/min` | an interactive human logs in a handful of times an hour; 20/min still lets a shared NAT through while capping bcrypt work |
| `LOGIN_ACCOUNT_FAILURE_LIMIT` | `5` | five wrong passwords in one window is a human typo at worst, and stops a 6th guess; below the ~10^10 online guesses needed for a weak password |
| `LOGIN_ACCOUNT_WINDOW_SECONDS` | `900` (15 min) | long enough to make online guessing pointless, short enough that a mistaken lock-out is a coffee break |
| `REFRESH_IP_RATE` | `30/min` | access tokens last 24h and the client refreshes single-flight, so 30/min is ~2 orders of magnitude above legitimate use |
| `REFRESH_SESSION_RATE` | `10/min` | per verified token subject; bounds rotation (and therefore blacklist writes) of a stolen token |
| `TRUST_X_FORWARDED_FOR` | `False` (`True` in prod) | client-controlled header, only trusted behind a rewriting proxy |

## 12. Tests

`apps/accounts/tests/test_auth_throttling.py` — 34 hermetic tests driving the real
endpoints through the API (no network, no live Redis):

* **Login (13)**: correct credentials never throttled; the generic 401 is
  unchanged; budget exhaustion → 429 with a truthful `Retry-After`; a refused
  attempt never reaches `check_password` (mocked to raise if called); a blocked
  response is byte-identical for existing and unknown accounts; success clears
  the budget; the block expires with its window; a sustained attack cannot extend
  or clear it; per-address ceilings counted per client; a spoofed
  `X-Forwarded-For` ignored; a trusted proxy honoured; no credential or address in
  the cache; disabled accounts unchanged and spending no budget.
* **Refresh (8)**: legitimate bursts stay inside the limit; the subject budget
  throttles repetition; **rotation does not reset the subject budget**; a reused
  rotated token is still rejected; the address ceiling covers invalid and missing
  tokens; a forged token cannot spend another account's budget (and the budget is
  still real afterwards); subject history expires; login and refresh budgets are
  independent.
* **Cache failure (4)**: login, wrong password and refresh all still work with
  every cache operation raising, and the outage is reported exactly once.
* **Keying (6)**: opaque, stable, case/whitespace-insensitive digest; proxy
  trust on/off; left-most XFF entry; `"unknown"` fallback; per-scope cache
  namespaces; throttles inert when disabled.
* **Production settings (3)**: Redis used when `REDIS_URL` is set; loud warning
  plus LocMemCache when it is not; production trusts the edge proxy.

`apps/accounts/tests/test_auth_throttle_cache_integration.py` — 4 opt-in tests
against a **real Redis**, gated on `CETRAK_REDIS_INTEGRATION=1` (the same
convention as the Celery integration tests). They exist because the bounded
lock-out of §7 depends on cache *backend* behaviour, not on our code: `add` is
create-only, `incr` is atomic, and **`incr` does not re-arm the TTL**, verified
behaviourally (a 2-second key incremented half way through its life is gone
afterwards). The file deliberately never calls `cache.clear()`, because on Redis
that is a `FLUSHDB` of the whole cache database and these tests run against a
developer's own Redis. **Not run here: no Redis is reachable on this machine
(`Test-NetConnection localhost:6379` → False), so these 4 remain skipped.**

## 13. Regression results

| Gate | Result |
| --- | --- |
| New throttling tests | **34 passed, 4 skipped** (skips = the opt-in Redis file) |
| `apps/accounts` | **143 passed, 4 skipped** |
| Full backend suite | **572 passed, 6 skipped, 16 subtests passed** (baseline 538 + 34) |
| `makemigrations --check --dry-run` | No changes detected |
| `npm run build` | clean — 157 modules, 444.15 kB JS / 123.75 kB gzip, 11.67 kB CSS |
| `npm run lint` | 13 problems (12 errors, 1 warning) — identical to the locked baseline, zero new |
| `git diff --check` | clean |

Skips: 1 pre-existing + 1 opt-in Celery broker round-trip + the 4 opt-in Redis
tests. The two pre-existing baseline skips are unchanged.

## 14. Migration verification

None required. No model, field, index or data change; throttle state is cache-only
by design (a login-attempt table would add a database write to every failed
login — the exact amplification this control exists to stop).

## 15. Defects found and fixed during this work

Recorded because each was found by a test, not by review:

1. **Double counting.** The first failure both `add`ed the counter and `incr`ed
   it, so the budget was spent in 3 failures instead of 5. `record_failure` now
   returns early on the create.
2. **No `Retry-After` header.** DRF 3.17 changed the contract: `check_throttles`
   asks each refusing throttle for `wait()`, not `duration`. `LoginAccountThrottle`
   inherited `BaseThrottle.wait()` → `None` → a 429 with no retry hint.
   `wait()` is now implemented; the header is asserted in a test.
3. **Sub-second `Retry-After`.** `blocked_seconds` truncated, so a client told to
   retry in `n` seconds could arrive 0.9s early and be refused again. It now
   rounds up, so waiting exactly as long as advertised is always sufficient.
4. **Off-by-one in the XFF test.** The test asserted the 3rd request from a
   2/min ceiling was refused; it is the 4th. The rewritten test is now *stronger*:
   the 3rd must succeed (proving the bucket follows the client, not the socket)
   and the 4th must be refused.
5. **Flaky window test.** A 1-second window expired while two bcrypt
   verifications were still running. The test now sleeps exactly the window the
   lock-out published, so it cannot be flaky on a slow machine.

## 16. Security review

* `services/api.js` session/auth behaviour otherwise untouched; the refresh
  contract, cookie flags, CSRF flow and `refreshPromise` single-flight are intact.
* No secret, address or credential is stored or logged (test-enforced).
* The refusal path runs **before** password verification, so a blocked attacker
  cannot even use the endpoint to keep the server busy hashing.
* Rate state cannot be manipulated by the client: addresses come from the socket
  or a trusted proxy, the account key is keyed server-side, and the refresh
  subject is taken only from a signature-verified claim.
* Fail-open on cache errors is deliberate and loud, and is the one documented
  availability trade-off (§17).
* Disabled accounts keep their existing 403 and spend no budget, so an attacker
  cannot distinguish "disabled" from "wrong password" faster than before.

## 17. Known limitations (documented, not defects)

1. **A still-throttled refresh ends the session in the UI.** A refresh that
   returns 429 twice is treated like any other failed refresh (session cleared,
   redirect to `/login`). Changing that would alter the session contract, which is
   out of scope here; the retry makes the transient case transparent.
2. **Redis behaviour is unverified on this machine.** The TTL-preservation
   property that the bounded lock-out rests on is proven against LocMem and
   asserted structurally for Redis, but the 4 opt-in tests were skipped (no local
   Redis). Run them with `CETRAK_REDIS_INTEGRATION=1` against a real instance
   before relying on a multi-worker deployment.
3. **`render.yaml` was not changed**, so a deployment without `REDIS_URL` boots
   with process-local counters and a loud warning. Adding the variable is a
   deployment change and deliberately left to the operator.
4. **The address layer is per address, not per ASN/person.** A botnet with N
   addresses gets N budgets; the per-account and per-subject layers are what make
   that ineffective.
5. Limits are single-tenant-per-account and unaware of user identity tier; there
   is no privileged "admin" bypass, by design — an auditor should be throttled
   like everyone else.
6. No alerting on repeated exhaustion. The `WARNING` log is the signal; wiring it
   into monitoring is a follow-up, not part of this control.

## 18. Files changed

| File | Change |
| --- | --- |
| `backend/apps/accounts/throttling.py` | new — 4 throttle classes, proxy-aware and opaque keying |
| `backend/apps/accounts/services.py` | `LoginAttemptService` + failure/success recording in `AuthService.login` |
| `backend/apps/accounts/views.py` | `@throttle_classes` on login and refresh |
| `backend/config/settings/base.py` | `AUTH_THROTTLE` block |
| `backend/config/settings/prod.py` | Redis cache when `REDIS_URL` is set, else loud LocMem fallback; trust the edge proxy |
| `backend/config/settings/test.py` | throttles off, LocMemCache pinned |
| `backend/apps/accounts/tests/test_auth_throttling.py` | new — 34 tests |
| `backend/apps/accounts/tests/test_auth_throttle_cache_integration.py` | new — 4 opt-in Redis tests |
| `backend/.env.example` | documents `REDIS_URL`'s production role and the Redis integration flag |
| `frontend/src/services/api.js` | bounded `Retry-After` retry for a throttled refresh |

## 19. Commit and final status

* Commit: `feat(auth): add login and refresh throttling`
* **AUD-014: CLOSED**, subject to the one open item in §17.2 (run the opt-in Redis
  tests in a multi-worker deployment) and the operator action in §17.3 (set
  `REDIS_URL`). No push and no deployment is performed by this work.

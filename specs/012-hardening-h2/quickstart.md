# Manual Verification: 012-H2 (browser)

No UI test harness exists; verify the cookie session flow by hand.

## Prereqs

- Backend up (`py manage.py runserver`), frontend dev server up.
- Browser DevTools → Application → Cookies → `localhost`.

## Flow

1. **Login** → response must NOT contain `refresh`; Cookie panel shows `refresh_token` (HttpOnly checkbox ON) and `csrftoken`; localStorage has only `accessToken` + `user`/`tenants`/`activeTenant`.
2. **Refresh after idle** → leave tab open past the 30-min access expiry (or shorten `ACCESS_TOKEN_LIFETIME` in test settings) → a request auto-refreshes: Network shows `POST /api/v1/auth/refresh/` without body token, succeeds, access updated; no 401 spinner.
3. **Logout** → sends `X-CSRFToken` from the `csrftoken` cookie; `refresh_token` cookie is cleared; UI returns to login.
4. **Switch tenant** → pick another tenant → `POST /tenants/switch/{id}` → `refresh_token` cookie set to new value; subsequent reports stay scoped to that tenant after refresh.
5. **Invitation binding** → invite `a@x.com`; register with `B@x.co` using the link → error message, no account created; back out and register `A@x.com ` → succeeds.
6. **Disable member** (Team page) → click Disable with the invitee selected → that user's next login/request gets 401/403; click Enable → access restored.
7. **CSRF** → in DevTools console delete the `csrftoken` cookie, then logout/refresh → 403.

## Negative checks

- `refresh_token` cookie is HttpOnly (not visible to `document.cookie`).
- No `refresh` value anywhere in the app's storage/localStorage after login, switch, or refresh.
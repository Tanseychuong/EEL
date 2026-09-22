# `apps/accounts`

Who can log in, and their tier. Nothing opportunity-specific lives here —
that's `apps/opportunities`.

## Files

| File | Purpose |
|---|---|
| `models.py` | Custom `User` (`AbstractBaseUser` + `PermissionsMixin`), email login |
| `forms.py` | `UserCreationForm`/`UserChangeForm` overrides — required because Django's defaults assume a `username` field, which this model doesn't have |
| `admin.py` | Registers `User` with Django admin; this is also where you assign the **Moderators group** to a user (see below) |
| `serializers.py` | `RegisterSerializer` (write), `UserSerializer` (read — used by `/me` and embedded wherever a user's public info shows up, e.g. `Opportunity.posted_by`) |
| `views.py` | `RegisterView`, `MeView` — login/refresh don't need custom views, they use SimpleJWT's built-ins directly |
| `urls.py` | `/api/auth/register`, `/login`, `/refresh`, `/me` |

## The three access tiers, and where each lives

| Tier | How it's determined |
|---|---|
| **Free user** | Default — any registered user with `is_premium=False` |
| **Premium user** | `user.is_premium_active()` — `True` if `is_premium=True` and (`premium_expires_at` is null OR in the future) |
| **Moderator** | `user.is_moderator()` — `True` if `is_superuser` OR the user has the `opportunities.can_verify_opportunity` permission |
| **Admin** | `is_superuser=True` (also makes `is_moderator()` true automatically — admins don't need the separate permission) |

`is_staff=True` is a separate flag from all of the above — it's what lets someone log into `/admin/` at all. **Moderators need `is_staff=True` set** or they won't be able to reach the admin screens they need to verify opportunities from.

## Assigning a moderator (once `opportunities` exists)

1. In `/admin/`, go to **Groups**, create a group called `Moderators`, and add the `opportunities | opportunity | Can verify opportunity` permission to it (this permission is defined in `opportunities/models.py`'s `Meta.permissions` — doesn't exist until that app is filled in).
2. Edit the target user, set `is_staff=True`, and add them to the `Moderators` group.

No custom endpoint, no code change, per new moderator — this is the point of using Django's built-in permission system instead of a custom role field.

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | none | create an account (always `is_premium=False`, `is_staff=False`) |
| POST | `/api/auth/login` | none | returns `access` + `refresh` JWT tokens (SimpleJWT default response shape) |
| POST | `/api/auth/refresh` | none (refresh token in body) | returns a new `access` token |
| GET | `/api/auth/me` | Bearer token | current user's profile, including computed `role` and `is_premium_active` |

## Not yet built

Nothing — this app is functionally complete for what's currently planned (registration, login, profile). Premium is granted from `/admin/` directly (edit the user, toggle `is_premium`) rather than through an API endpoint, since there's no payment flow yet.

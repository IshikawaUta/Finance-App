"""PyTauri IPC command definitions.

Every command is a thin adapter: authenticate, call a service, translate
errors.  Command names are part of the public contract — see
``docs/ipc-contract.md`` before renaming anything.
"""

from __future__ import annotations

import logging
from typing import Annotated

from anyio import to_thread
from pytauri import Commands, State

from finance_app import services
from finance_app.auth import (
    burn_password_time,
    create_access_token,
    hash_password,
    require_user,
    verify_password,
)
from finance_app.errors import AppError, api_errors
from finance_app.models import User, utcnow
from finance_app.schemas import (
    AuthResponse,
    CategoriesResponse,
    DashboardRequest,
    DashboardResponse,
    HealthResponse,
    LoginRequest,
    OkResponse,
    RegisterRequest,
    SetConnectionRequest,
    SystemStatus,
    TokenRequest,
    TransactionCreateRequest,
    TransactionDeleteRequest,
    TransactionListRequest,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdateRequest,
    UserOut,
    WalletCreateRequest,
    WalletDeleteRequest,
    WalletListResponse,
    WalletOut,
    WalletUpdateRequest,
)
from finance_app.state import AppState

logger = logging.getLogger(__name__)

commands: Commands = Commands()


# ---------------------------------------------------------------------------
# System / configuration (no authentication required)
# ---------------------------------------------------------------------------


@commands.command()
async def health(state: Annotated[AppState, State()]) -> HealthResponse:
    """Liveness probe used by the frontend during startup."""

    return HealthResponse(version=state.config.version, uptime_seconds=state.uptime_seconds)


@commands.command()
async def system_status(state: Annotated[AppState, State()]) -> SystemStatus:
    """Return backend/database status without leaking credentials."""

    with api_errors():
        return await state.status()


@commands.command()
async def config_set_mongodb(
    body: SetConnectionRequest,
    state: Annotated[AppState, State()],
) -> SystemStatus:
    """Test, persist and activate a new MongoDB connection (login/setup or Settings)."""

    with api_errors():
        return await state.reconfigure(body.uri, body.db_name)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@commands.command()
async def auth_register(
    body: RegisterRequest,
    state: Annotated[AppState, State()],
) -> AuthResponse:
    """Create an account and return a signed session token."""

    with api_errors():
        await state.db.ensure_connected()

        existing = await User.find_one({"email": body.email})
        if existing is not None:
            raise AppError("AUTH_EMAIL_TAKEN", "Email sudah terdaftar.")

        password_hash = await to_thread.run_sync(hash_password, body.password)
        user = User(
            email=body.email,
            name=body.name.strip(),
            password_hash=password_hash,
            base_currency=body.base_currency,
            last_login_at=utcnow(),
        )
        await user.insert()

        assert user.id is not None
        token, expires_at = create_access_token(user.id, state.config)
        logger.info("Registered user %s", user.id)
        return AuthResponse(token=token, expires_at=expires_at, user=UserOut.from_doc(user))


@commands.command()
async def auth_login(
    body: LoginRequest,
    state: Annotated[AppState, State()],
) -> AuthResponse:
    """Authenticate with email/password and issue a JWT."""

    with api_errors():
        await state.db.ensure_connected()

        user = await User.find_one({"email": body.email})
        if user is None:
            await to_thread.run_sync(burn_password_time)
            raise AppError("AUTH_INVALID_CREDENTIALS", "Email atau password salah.")

        valid = await to_thread.run_sync(verify_password, user.password_hash, body.password)
        if not valid:
            raise AppError("AUTH_INVALID_CREDENTIALS", "Email atau password salah.")

        user.last_login_at = utcnow()
        user.updated_at = utcnow()
        await user.save()

        assert user.id is not None
        token, expires_at = create_access_token(user.id, state.config)
        return AuthResponse(token=token, expires_at=expires_at, user=UserOut.from_doc(user))


@commands.command()
async def auth_me(body: TokenRequest, state: Annotated[AppState, State()]) -> UserOut:
    """Validate a stored token and return the current profile."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return UserOut.from_doc(user)


@commands.command()
async def auth_logout(body: TokenRequest) -> OkResponse:
    """Stateless logout. The client discards the token; tokens expire in 30 days."""

    del body  # signature kept for a uniform client API
    return OkResponse(message="Berhasil keluar.")


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


@commands.command()
async def wallet_list(body: TokenRequest, state: Annotated[AppState, State()]) -> WalletListResponse:
    """List active wallets with computed balances."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.list_wallets(user)


@commands.command()
async def wallet_create(
    body: WalletCreateRequest,
    state: Annotated[AppState, State()],
) -> WalletOut:
    """Create a wallet for the current user."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.create_wallet(user, body)


@commands.command()
async def wallet_update(
    body: WalletUpdateRequest,
    state: Annotated[AppState, State()],
) -> WalletOut:
    """Update wallet metadata or initial balance."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.update_wallet(user, body)


@commands.command()
async def wallet_delete(
    body: WalletDeleteRequest,
    state: Annotated[AppState, State()],
) -> OkResponse:
    """Delete a wallet (optionally cascading its transactions)."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.delete_wallet(user, body)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@commands.command()
async def transaction_list(
    body: TransactionListRequest,
    state: Annotated[AppState, State()],
) -> TransactionListResponse:
    """Paginated, filterable transaction history."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.list_transactions(user, body, state.config)


@commands.command()
async def transaction_create(
    body: TransactionCreateRequest,
    state: Annotated[AppState, State()],
) -> TransactionOut:
    """Record an income or expense."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.create_transaction(user, body, state.config)


@commands.command()
async def transaction_update(
    body: TransactionUpdateRequest,
    state: Annotated[AppState, State()],
) -> TransactionOut:
    """Edit a transaction."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.update_transaction(user, body, state.config)


@commands.command()
async def transaction_delete(
    body: TransactionDeleteRequest,
    state: Annotated[AppState, State()],
) -> OkResponse:
    """Delete a transaction."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.delete_transaction(user, body.transaction_id)


# ---------------------------------------------------------------------------
# Dashboard & metadata
# ---------------------------------------------------------------------------


@commands.command()
async def dashboard_get(
    body: DashboardRequest,
    state: Annotated[AppState, State()],
) -> DashboardResponse:
    """Everything the dashboard needs in a single IPC round-trip."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.dashboard(user, body, state.config)


@commands.command()
async def categories_list(
    body: TokenRequest,
    state: Annotated[AppState, State()],
) -> CategoriesResponse:
    """Default categories merged with categories already used by the user."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.categories(user)


@commands.command()
async def demo_seed(body: TokenRequest, state: Annotated[AppState, State()]) -> OkResponse:
    """Populate an empty account with realistic demo data."""

    with api_errors():
        await state.db.ensure_connected()
        user = await require_user(body.token, state.config)
        return await services.seed_demo(user, state.config)

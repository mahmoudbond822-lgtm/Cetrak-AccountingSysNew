"""The test database backend selector is load-bearing, so it is tested.

``config.settings.test`` decides which database the entire suite runs against,
and it does so before any test executes. A wrong answer here is not a failing
assertion, it is a whole suite that quietly tests the wrong engine -- which is
exactly how ``apps/accounting/migrations/0005`` (a PostgreSQL-only CHECK
constraint that SQLite ignores) went unnoticed behind a green build.

The resolver is called directly with a stand-in environment, so these tests need
neither a database connection nor a subprocess, and they cannot disturb the
database the rest of the suite is using.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.test import _POSTGRES_ENV, _database_config

POSTGRES = {
    "POSTGRES_DB": "cetrak",
    "POSTGRES_USER": "cetrak",
    "POSTGRES_PASSWORD": "cetrak",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "55432",
}

SQLITE_ENGINE = "django.db.backends.sqlite3"
POSTGRES_ENGINE = "django.db.backends.postgresql"


def engine(env):
    return _database_config(env)["default"]["ENGINE"]


def without(env, *names):
    return {k: v for k, v in env.items() if k not in names}


class TestUnsetSelectorKeepsTheHistoricalInference:
    """With no CETRAK_TEST_DB, the old all-four-or-SQLite rule is intact.

    Every existing local invocation depends on this, including the documented
    ones that export the POSTGRES_* variables by hand.
    """

    def test_all_four_variables_select_postgres(self):
        assert engine(dict(POSTGRES)) == POSTGRES_ENGINE

    @pytest.mark.parametrize("missing", _POSTGRES_ENV)
    def test_a_partial_set_selects_sqlite(self, missing):
        assert engine(without(POSTGRES, missing)) == SQLITE_ENGINE

    def test_an_empty_variable_counts_as_missing(self):
        assert engine(dict(POSTGRES, POSTGRES_PASSWORD="")) == SQLITE_ENGINE

    def test_nothing_set_selects_in_memory_sqlite(self):
        assert engine({}) == SQLITE_ENGINE

    def test_postgres_connection_details_are_passed_through(self):
        assert _database_config(dict(POSTGRES))["default"] == {
            "ENGINE": POSTGRES_ENGINE,
            "NAME": "cetrak",
            "USER": "cetrak",
            "PASSWORD": "cetrak",
            "HOST": "127.0.0.1",
            "PORT": "55432",
        }

    def test_the_port_defaults_to_5432(self):
        default = _database_config(without(POSTGRES, "POSTGRES_PORT"))["default"]
        assert default["PORT"] == "5432"


class TestExplicitSelector:
    """CETRAK_TEST_DB makes the choice declared rather than inferred."""

    @pytest.mark.parametrize("value", ["postgres", "POSTGRES", "  Postgres  "])
    def test_postgres_is_selected(self, value):
        assert engine(dict(POSTGRES, CETRAK_TEST_DB=value)) == POSTGRES_ENGINE

    def test_sqlite_is_selected(self):
        assert engine(dict(CETRAK_TEST_DB="sqlite")) == SQLITE_ENGINE

    def test_sqlite_wins_over_ambient_postgres_variables(self):
        """The fast job must not drift onto PostgreSQL by accident."""
        default = _database_config(dict(POSTGRES, CETRAK_TEST_DB="sqlite"))["default"]
        assert default["ENGINE"] == SQLITE_ENGINE
        assert default["NAME"] == ":memory:"

    def test_an_empty_value_behaves_as_unset(self):
        assert engine(dict(POSTGRES, CETRAK_TEST_DB="  ")) == POSTGRES_ENGINE

    def test_an_unknown_value_is_rejected(self):
        with pytest.raises(ImproperlyConfigured) as caught:
            _database_config(dict(POSTGRES, CETRAK_TEST_DB="mysql"))
        assert "CETRAK_TEST_DB" in str(caught.value)

    @pytest.mark.parametrize(
        "env",
        [dict(CETRAK_TEST_DB="sqlite"), dict(POSTGRES, CETRAK_TEST_DB="sqlite")],
    )
    def test_each_call_returns_an_independent_config(self, env):
        """Callers must not share one dict.

        Django's test runner rewrites ``settings.DATABASES["default"]["NAME"]``
        in place when it creates the test database, so a resolver that returned a
        shared object would hand out the rewritten value for the rest of the
        process. That corruption is invisible in a single-test run and appears
        only once the whole suite has set up its databases, which is exactly the
        kind of failure a fast edit/run loop would never show and CI would.
        """
        first = _database_config(env)
        first["default"]["NAME"] = "corrupted-by-caller"

        second = _database_config(env)
        assert second["default"]["NAME"] == ":memory:"


class TestIncompletePostgresFailsLoudly:
    """Asking for PostgreSQL without the details is a build failure.

    This is the point of the explicit selector. Under the historical inference
    the same environment produces a green SQLite run, and the PostgreSQL-only
    migrations are never executed.
    """

    @pytest.mark.parametrize("missing", _POSTGRES_ENV)
    def test_the_missing_variable_is_named(self, missing):
        env = dict(without(POSTGRES, missing), CETRAK_TEST_DB="postgres")
        with pytest.raises(ImproperlyConfigured) as caught:
            _database_config(env)
        assert missing in str(caught.value)

    def test_nothing_set_at_all_is_rejected(self):
        with pytest.raises(ImproperlyConfigured):
            _database_config({"CETRAK_TEST_DB": "postgres"})

    def test_the_error_explains_why_it_does_not_fall_back(self):
        with pytest.raises(ImproperlyConfigured) as caught:
            _database_config({"CETRAK_TEST_DB": "postgres"})
        assert "refusing to fall back to SQLite" in str(caught.value)


class TestTheSuiteRunsOnTheDeclaredBackend:
    """The declared value has to survive into the live connection.

    ``_database_config`` returning the right answer is not sufficient if some
    other layer overrides ``DATABASES`` afterwards, so this asserts on the
    resolved settings and on the connection Django actually opened.
    """

    def test_the_resolved_engine_is_one_of_the_two_supported_backends(self):
        from django.conf import settings

        assert settings.DATABASES["default"]["ENGINE"] in {
            SQLITE_ENGINE,
            POSTGRES_ENGINE,
        }

    def test_the_open_connection_agrees_with_the_resolved_engine(self):
        from django.conf import settings
        from django.db import connection

        expected = (
            "postgresql"
            if settings.DATABASES["default"]["ENGINE"] == POSTGRES_ENGINE
            else "sqlite"
        )
        assert connection.vendor == expected


@pytest.mark.parametrize(
    "env",
    [
        {},
        dict(POSTGRES),
        dict(CETRAK_TEST_DB="sqlite"),
        dict(POSTGRES, CETRAK_TEST_DB="sqlite"),
    ],
)
def test_the_selector_never_needs_a_database_connection(env):
    """Resolution is pure: it must not touch a connection to answer."""
    assert set(_database_config(env)) == {"default"}

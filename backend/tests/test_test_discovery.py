"""Unit tests for static test file discovery and classification."""

import pytest

from backend.app.services.dependency_impact.test_discovery import (
    TEST_TYPE_CONFIG,
    TEST_TYPE_E2E,
    TEST_TYPE_INTEGRATION,
    TEST_TYPE_UNIT,
    TEST_TYPE_UNKNOWN,
    classify_test_type,
    discover_test_files,
    discover_test_files_from_nodes,
    is_test_file,
)


def test_is_test_file_standard_suffixes():
    assert is_test_file("src/services/payment.test.ts") is True
    assert is_test_file("src/services/payment.spec.ts") is True
    assert is_test_file("src/components/Button.test.tsx") is True
    assert is_test_file("src/components/Button.spec.jsx") is True
    assert is_test_file("tests/unit/test_payment.py") is True
    assert is_test_file("tests/payment_test.py") is True
    assert is_test_file("src/test/PaymentTest.java") is True


def test_is_test_file_in_test_directories():
    assert is_test_file("tests/payment.ts") is True
    assert is_test_file("test/auth.js") is True
    assert is_test_file("src/__tests__/Button.tsx") is True
    assert is_test_file("spec/models/user_spec.rb") is False  # .rb not in supported extensions
    assert is_test_file("spec/models/user.ts") is True


def test_is_test_file_non_test_files_rejected():
    assert is_test_file("src/services/payment.ts") is False
    assert is_test_file("src/testing.ts") is False
    assert is_test_file("src/contest.ts") is False
    assert is_test_file("src/latest.ts") is False
    assert is_test_file("src/test-utils.ts") is False
    assert is_test_file("tests/helpers/test-helper.ts") is False
    assert is_test_file("tests/fixtures/mockData.ts") is False


def test_is_test_file_ignored_directories_rejected():
    assert is_test_file("node_modules/pkg/index.test.js") is False
    assert is_test_file(".git/hooks/test.sh") is False
    assert is_test_file("dist/tests/app.test.js") is False
    assert is_test_file("build/test.js") is False
    assert is_test_file(".venv/lib/site-packages/test.py") is False


def test_is_test_file_windows_backslashes():
    assert is_test_file(r"tests\unit\payment.test.ts") is True
    assert is_test_file(r"src\__tests__\Button.test.tsx") is True


def test_classify_test_type():
    assert classify_test_type("src/e2e/login.spec.ts") == TEST_TYPE_E2E
    assert classify_test_type("cypress/e2e/checkout.cy.ts") == TEST_TYPE_E2E
    assert classify_test_type("tests/e2e/flow.e2e.test.ts") == TEST_TYPE_E2E

    assert classify_test_type("tests/integration/payment.integration.test.ts") == TEST_TYPE_INTEGRATION
    assert classify_test_type("tests/integration/db.test.ts") == TEST_TYPE_INTEGRATION

    assert classify_test_type("tests/setupTests.ts") == TEST_TYPE_CONFIG
    assert classify_test_type("tests/jest.setup.js") == TEST_TYPE_CONFIG

    assert classify_test_type("src/services/payment.test.ts") == TEST_TYPE_UNIT
    assert classify_test_type("src/services/auth.spec.ts") == TEST_TYPE_UNIT
    assert classify_test_type("tests/unit/app.test.ts") == TEST_TYPE_UNIT


def test_discover_test_files_from_nodes():
    nodes = [
        "src/app.ts",
        "src/utils.ts",
        "tests/app.test.ts",
        "tests/integration/api.test.ts",
        "src/e2e/flow.spec.ts",
        "src/contest.ts",
    ]

    discovered = discover_test_files_from_nodes(nodes)
    assert len(discovered) == 3
    paths = [d["file_path"] for d in discovered]
    assert paths == ["src/e2e/flow.spec.ts", "tests/app.test.ts", "tests/integration/api.test.ts"]

    types = {d["file_path"]: d["test_type"] for d in discovered}
    assert types["src/e2e/flow.spec.ts"] == TEST_TYPE_E2E
    assert types["tests/app.test.ts"] == TEST_TYPE_UNIT
    assert types["tests/integration/api.test.ts"] == TEST_TYPE_INTEGRATION


def test_discover_test_files_empty():
    assert discover_test_files(repo_path=None, graph_nodes=[]) == []
    assert discover_test_files_from_nodes([]) == []


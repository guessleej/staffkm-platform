"""Agent service smoke tests（CI gate 最小覆蓋）。

僅驗證模組能 import、settings 可載入；不啟動 server / DB。
真實整合測試走 tools/e2e（Playwright）。
"""


def test_import_main():
    from app import main  # noqa: F401


def test_import_executor():
    from app.core.workflow import executor  # noqa: F401
    assert hasattr(executor, "WorkflowExecutor")


def test_providers_registry_has_all_adapters():
    from app.core.providers import PROVIDER_REGISTRY, get_adapter
    # 至少 20 家
    assert len(PROVIDER_REGISTRY) >= 20
    # 每筆都能解出 adapter（不會 raise）
    for meta in PROVIDER_REGISTRY:
        adapter = get_adapter(meta.type)
        assert adapter is not None


def test_media_registry_has_5_entries():
    from app.core.media import MEDIA_PROVIDER_REGISTRY
    assert len(MEDIA_PROVIDER_REGISTRY) >= 5

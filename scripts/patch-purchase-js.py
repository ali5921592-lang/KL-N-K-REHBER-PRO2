#!/usr/bin/env python3
"""Patch the capacitor-plugin-cdv-purchase JS adapter for early product events.

The upstream adapters.initialize() waits for both loadProducts() and
loadReceipts() when the Apple adapter advertises supportsParallelLoading.  The
Apple StoreKit product list can already be available while AppTransaction/
receipt loading is slow or unavailable.  Because productsUpdated() was emitted
only after Promise.all(), the paywall stayed in a loading state even when
StoreKit had returned a valid product.

This patch notifies the store about loaded products as soon as loadProducts()
resolves, while preserving the existing receipt loading and initialization
result handling.  It is idempotent and supports an optional path for local
verification.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [ROOT / "node_modules" / "capacitor-plugin-cdv-purchase" / "dist" / "index.js"]
MARKER = "productsUpdated early before receipts"

OLD = """                        let loadProductsResult = [];
                        let loadReceiptsResult = [];
                        if (platformProducts.length > 0) {
                            if (adapter.supportsParallelLoading) {
                                [loadProductsResult, loadReceiptsResult] = yield Promise.all([
                                    adapter.loadProducts(platformProducts),
                                    adapter.loadReceipts()
                                ]);
                            }
                            else {
                                loadProductsResult = yield adapter.loadProducts(platformProducts);
                                loadReceiptsResult = yield adapter.loadReceipts();
                            }
                            log.info(`${adapter.name} products loaded: ${JSON.stringify(loadProductsResult)}`);
                            const loadedProducts = loadProductsResult.filter(p => p instanceof CdvPurchase.Product);
                            context.listener.productsUpdated(platformToInit.platform, loadedProducts);
                            log.info(`${adapter.name} receipts loaded: ${JSON.stringify(loadReceiptsResult)}`);
                        }
"""

NEW = """                        let loadProductsResult = [];
                        let loadReceiptsResult = [];
                        let productsNotified = false;
                        const notifyProductsEarly = (result) => {
                            if (productsNotified)
                                return;
                            productsNotified = true;
                            const loadedProducts = result.filter(p => p instanceof CdvPurchase.Product);
                            context.listener.productsUpdated(platformToInit.platform, loadedProducts);
                            log.info(`${adapter.name} productsUpdated early before receipts: ${JSON.stringify(loadedProducts)}`);
                        };
                        if (platformProducts.length > 0) {
                            if (adapter.supportsParallelLoading) {
                                const productsPromise = adapter.loadProducts(platformProducts).then(result => {
                                    notifyProductsEarly(result);
                                    return result;
                                });
                                [loadProductsResult, loadReceiptsResult] = yield Promise.all([
                                    productsPromise,
                                    adapter.loadReceipts()
                                ]);
                            }
                            else {
                                loadProductsResult = yield adapter.loadProducts(platformProducts);
                                notifyProductsEarly(loadProductsResult);
                                loadReceiptsResult = yield adapter.loadReceipts();
                            }
                            log.info(`${adapter.name} products loaded: ${JSON.stringify(loadProductsResult)}`);
                            log.info(`${adapter.name} receipts loaded: ${JSON.stringify(loadReceiptsResult)}`);
                        }
"""


def paths() -> list[Path]:
    if len(sys.argv) > 1:
        return [Path(arg).resolve() for arg in sys.argv[1:]]
    return DEFAULT_PATHS


def patch(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return "already-patched"
    if OLD not in text:
        raise RuntimeError(f"Beklenen adapters.initialize() bloğu bulunamadı: {path}")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    return "patched"


def main() -> int:
    files = [path for path in paths() if path.exists()]
    if not files:
        raise RuntimeError("capacitor-plugin-cdv-purchase/dist/index.js bulunamadı.")
    statuses = []
    for path in files:
        statuses.append((path, patch(path)))
    for path, status in statuses:
        print(f"[patch-purchase-js] {status}: {path}")
    if not any(MARKER in path.read_text(encoding="utf-8") for path, _ in statuses):
        raise RuntimeError("Early productsUpdated patch doğrulanamadı.")
    print("[patch-purchase-js] Ürünler receipt yüklemesini beklemeden productsUpdated ile bildirilecek.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

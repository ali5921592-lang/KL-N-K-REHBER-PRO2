#!/usr/bin/env python3
"""Patch the Capacitor PurchasePlugin native source used by the iOS build.

The upstream plugin's init() waits for Transaction.currentEntitlements before
resolving the Capacitor promise. StoreKit documents that sequence as a finite
snapshot, but a delayed StoreKit/TestFlight response can still block the whole
product-loading pipeline. Current-entitlement notifications do not need to
block product metadata loading, so resolve the bridge call immediately and
keep the entitlement scan in the background.

The script is intentionally idempotent and supports both node_modules (before
cap sync) and CocoaPods' copied source (after cap sync).
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = [
    ROOT / "node_modules" / "capacitor-plugin-cdv-purchase",
    ROOT / "ios" / "App" / "Pods",
]

OLD = """        // Load current entitlements and emit to JS so existing subscriptions
        // are visible immediately on app launch (without requiring a manual restore).
        Task {
            for await result in Transaction.currentEntitlements {
                switch result {
                case .verified(let transaction):
                    if transaction.isUpgraded {
                        debugLog(\"init: skipping upgraded entitlement id=\\(transaction.id) product=\\(transaction.productID)\")
                        continue
                    }
                    if self.sk2.processedTransactionIds.contains(transaction.id) {
                        debugLog(\"init: skipping already-processed entitlement id=\\(transaction.id)\")
                        continue
                    }
                    self.sk2.processedTransactionIds.insert(transaction.id)
                    self.sk2.unfinishedTransactions[String(transaction.id)] = transaction
                    await self.emitTransactionUpdate(transaction,
                        state: \"PaymentTransactionStateRestored\",
                        jwsRepresentation: result.jwsRepresentation)
                case .unverified(let transaction, let error):
                    debugLog(\"init: unverified entitlement id=\\(transaction.id) product=\\(transaction.productID) error=\\(error)\")
                }
            }
            call.resolve()
        }
"""

NEW = """        // Product metadata loading must not wait for the entitlement snapshot.
        // StoreKit documents currentEntitlements as a finite sequence, but a
        // delayed TestFlight/Sandbox response can otherwise keep the Capacitor
        // init Promise pending and prevent Product.products(for:) from running.
        call.resolve()

        // Load current entitlements in the background so existing subscriptions
        // are still emitted to JS without blocking product metadata loading.
        Task {
            debugLog(\"init: current entitlement scan started\")
            for await result in Transaction.currentEntitlements {
                switch result {
                case .verified(let transaction):
                    if transaction.isUpgraded {
                        debugLog(\"init: skipping upgraded entitlement id=\\(transaction.id) product=\\(transaction.productID)\")
                        continue
                    }
                    if self.sk2.processedTransactionIds.contains(transaction.id) {
                        debugLog(\"init: skipping already-processed entitlement id=\\(transaction.id)\")
                        continue
                    }
                    self.sk2.processedTransactionIds.insert(transaction.id)
                    self.sk2.unfinishedTransactions[String(transaction.id)] = transaction
                    await self.emitTransactionUpdate(transaction,
                        state: \"PaymentTransactionStateRestored\",
                        jwsRepresentation: result.jwsRepresentation)
                case .unverified(let transaction, let error):
                    debugLog(\"init: unverified entitlement id=\\(transaction.id) product=\\(transaction.productID) error=\\(error)\")
                }
            }
            debugLog(\"init: current entitlement scan completed\")
        }
"""


def candidates() -> list[Path]:
    found: list[Path] = []
    for root in SEARCH_ROOTS:
        if root.exists():
            found.extend(root.rglob("PurchasePlugin.swift"))
    # Preserve order while removing duplicates (for symlinked Pods trees).
    return list(dict.fromkeys(found))


def patch(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if NEW in text:
        return "already-patched"
    if OLD not in text:
        raise RuntimeError(f"Beklenen PurchasePlugin.init() bloğu bulunamadı: {path}")
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    return "patched"


def main() -> int:
    files = candidates()
    if not files:
        raise RuntimeError(
            "PurchasePlugin.swift bulunamadı. Önce npm install / npx cap sync ios çalıştırılmalı."
        )
    statuses = []
    for path in files:
        statuses.append((path, patch(path)))
    for path, status in statuses:
        print(f"[patch-purchase-plugin] {status}: {path}")
    # At least one source must contain the patched implementation.
    if not any(NEW in path.read_text(encoding="utf-8") for path, _ in statuses):
        raise RuntimeError("Native PurchasePlugin patch doğrulanamadı.")
    print("[patch-purchase-plugin] init() artık entitlement taramasını beklemeden resolve ediyor.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[patch-purchase-plugin] HATA: {exc}", file=sys.stderr)
        raise

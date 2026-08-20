"""Patch capacitor-plugin-cdv-purchase for reliable product events and diagnostics.

The upstream Apple adapter waits for both product and receipt loading before
publishing productsUpdated. This patch publishes products as soon as the
product request resolves, records the native valid/invalid product payload in
a temporary window.__iapDiag object for the diagnostic build, and fixes the
upstream native-load error callback so a rejected Product.products(for:) call
does not leave loadProducts() pending forever.

The patch is idempotent and supports an optional path for local verification.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [ROOT / "node_modules" / "capacitor-plugin-cdv-purchase" / "dist" / "index.js"]
EARLY_MARKER = "productsUpdated early before receipts"
DIAG_MARKER = "nativeValidProducts"
ERROR_FIX_MARKER = "upstream callback returned an array without resolving"

EARLY_OLD = """                        let loadProductsResult = [];
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

EARLY_NEW = """                        let loadProductsResult = [];
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

LOAD_OLD = """            loadProducts(products) {
                return new Promise(resolve => {
                    this.log.info('bridge.load');
                    this.bridge.load(products.map(p => p.id), (validProducts, invalidProducts) => __awaiter(this, void 0, void 0, function* () {
                        this.log.info('bridge.loaded: ' + JSON.stringify({ validProducts, invalidProducts }));
                        this.addValidProducts(products, validProducts);
                        const eligibilities = yield this.loadEligibility(validProducts);
                        this.log.info('eligibilities ready: ' + JSON.stringify(eligibilities));
                        // for any valid product that includes a discount, check the eligibility.
                        const ret = products.map(p => {
                            if (invalidProducts.indexOf(p.id) >= 0) {
                                this.log.debug(`${p.id} is invalid`);
                                return appStoreError(CdvPurchase.ErrorCode.INVALID_PRODUCT_ID, 'Product not found in AppStore. #400', p.id);
                            }
                            else {
                                const valid = validProducts.find(v => v.id === p.id);
                                this.log.debug(`${p.id} is valid: ${JSON.stringify(valid)}`);
                                if (!valid)
                                    return appStoreError(CdvPurchase.ErrorCode.INVALID_PRODUCT_ID, 'Product not found in AppStore. #404', p.id);
                                let product = this.getProduct(p.id);
                                if (product) {
                                    this.log.debug('refreshing existing product');
                                    product === null || product === void 0 ? void 0 : product.refresh(valid, this.context.apiDecorators, eligibilities);
                                }
                                else {
                                    this.log.debug('registering new product');
                                    product = new AppleAppStore.SKProduct(valid, p, this.context.apiDecorators, eligibilities);
                                    this._products.push(product);
                                }
                                return product;
                            }
                        });
                        this.log.debug(`Products loaded: ${JSON.stringify(ret)}`);
                        resolve(ret);
                    }), (code, message) => {
                        return products.map(p => appStoreError(code, message, null));
                    });
                });
            }
"""

LOAD_NEW = """            loadProducts(products) {
                return new Promise(resolve => {
                    const requestedProductIds = products.map(p => p.id);
                    const recordDiagnostic = (data) => {
                        try {
                            if (typeof window === 'undefined')
                                return;
                            window.__iapDiag = Object.assign({}, window.__iapDiag || {}, data, {
                                requestedProductIds,
                                updatedAt: new Date().toISOString()
                            });
                        }
                        catch (_) { }
                    };
                    recordDiagnostic({
                        bridgeLoad: {
                            status: 'started',
                            requestedProductIds
                        }
                    });
                    this.log.info('bridge.load');
                    this.bridge.load(requestedProductIds, (validProducts, invalidProducts) => __awaiter(this, void 0, void 0, function* () {
                        validProducts = Array.isArray(validProducts) ? validProducts : [];
                        invalidProducts = Array.isArray(invalidProducts) ? invalidProducts : [];
                        recordDiagnostic({
                            bridgeLoad: {
                                status: 'success',
                                requestedProductIds,
                                validProducts: validProducts.map(vp => ({
                                    id: vp && vp.id || null,
                                    price: vp && (vp.price || vp.displayPrice) || null,
                                    currency: vp && vp.currency || null,
                                    billingPeriod: vp && vp.billingPeriod || null,
                                    billingPeriodUnit: vp && vp.billingPeriodUnit || null,
                                    group: vp && vp.group || null
                                })),
                                invalidProductIds: invalidProducts
                            },
                            nativeValidProducts: validProducts,
                            nativeInvalidProductIds: invalidProducts
                        });
                        this.log.info('bridge.loaded: ' + JSON.stringify({ validProducts, invalidProducts }));
                        this.addValidProducts(products, validProducts);
                        const eligibilities = yield this.loadEligibility(validProducts);
                        this.log.info('eligibilities ready: ' + JSON.stringify(eligibilities));
                        // for any valid product that includes a discount, check the eligibility.
                        const ret = products.map(p => {
                            if (invalidProducts.indexOf(p.id) >= 0) {
                                this.log.debug(`${p.id} is invalid`);
                                return appStoreError(CdvPurchase.ErrorCode.INVALID_PRODUCT_ID, 'Product not found in AppStore. #400', p.id);
                            }
                            else {
                                const valid = validProducts.find(v => v.id === p.id);
                                this.log.debug(`${p.id} is valid: ${JSON.stringify(valid)}`);
                                if (!valid)
                                    return appStoreError(CdvPurchase.ErrorCode.INVALID_PRODUCT_ID, 'Product not found in AppStore. #404', p.id);
                                let product = this.getProduct(p.id);
                                if (product) {
                                    this.log.debug('refreshing existing product');
                                    product === null || product === void 0 ? void 0 : product.refresh(valid, this.context.apiDecorators, eligibilities);
                                }
                                else {
                                    this.log.debug('registering new product');
                                    product = new AppleAppStore.SKProduct(valid, p, this.context.apiDecorators, eligibilities);
                                    this._products.push(product);
                                }
                                return product;
                            }
                        });
                        this.log.debug(`Products loaded: ${JSON.stringify(ret)}`);
                        resolve(ret);
                    }), (code, message) => {
                        const nativeMessage = (message === null || message === void 0 ? void 0 : message.toString()) || 'load failed';
                        recordDiagnostic({
                            bridgeLoad: {
                                status: 'error',
                                requestedProductIds,
                                code,
                                message: nativeMessage
                            },
                            nativeLoadError: nativeMessage
                        });
                        this.log.error(`${ERROR_FIX_MARKER}: ${code} - ${nativeMessage}`);
                        // The upstream callback returned an array without resolving
                        // the Promise, so a rejected Product.products(for:) request
                        // left store.initialize() pending forever.
                        resolve(products.map(p => appStoreError(code, nativeMessage, p.id)));
                    });
                });
            }
"""


def paths() -> list[Path]:
    if len(sys.argv) > 1:
        return [Path(arg).resolve() for arg in sys.argv[1:]]
    return DEFAULT_PATHS


def patch(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    changed = False
    if EARLY_MARKER not in text:
        if EARLY_OLD not in text:
            raise RuntimeError(f"Beklenen adapters.initialize() bloğu bulunamadı: {path}")
        text = text.replace(EARLY_OLD, EARLY_NEW, 1)
        changed = True
    if DIAG_MARKER not in text:
        if LOAD_OLD not in text:
            raise RuntimeError(f"Beklenen Apple loadProducts() bloğu bulunamadı: {path}")
        text = text.replace(LOAD_OLD, LOAD_NEW, 1)
        changed = True
    path.write_text(text, encoding="utf-8")
    if not changed:
        return "already-patched"
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
    for marker in (EARLY_MARKER, DIAG_MARKER, ERROR_FIX_MARKER):
        if not any(marker in path.read_text(encoding="utf-8") for path, _ in statuses):
            raise RuntimeError(f"JS patch doğrulanamadı: {marker}")
    print("[patch-purchase-js] Erken productsUpdated, native IAP tanısı ve load hata çözümü etkin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

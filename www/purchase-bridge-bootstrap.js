/*
 * Capacitor native purchase bridge bootstrap.
 * `cdv-purchase.bundle.js` is generated from capacitor-plugin-cdv-purchase.
 * It exposes the same CdvPurchase API used by the existing application code.
 */
(function () {
  'use strict';

  var mod = window.__CdvPurchaseModule || {};
  var api = mod.CdvPurchase || mod.default || mod;

  if (api && api.store && api.Platform && api.ProductType) {
    window.CdvPurchase = api;
    window.CdvPurchaseCapacitor = { installed: true };
    window.__iapNativeBridgeReady = true;
    try { window.dispatchEvent(new Event('cdvpurchase-ready')); } catch (e) {}
  } else {
    window.__iapNativeBridgeReady = false;
    window.__iapNativeBridgeError = 'Capacitor native PurchasePlugin bridge is unavailable';
  }
}());

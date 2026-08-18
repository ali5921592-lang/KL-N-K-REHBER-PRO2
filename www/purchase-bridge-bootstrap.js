/*
 * Capacitor native purchase bridge bootstrap.
 * `cdv-purchase.bundle.js` is generated from capacitor-plugin-cdv-purchase.
 * The global CdvPurchase API is exposed only after the Capacitor native
 * PurchasePlugin proxy is present, so the package cannot silently fall back
 * to an unavailable Cordova bridge.
 */
(function () {
  'use strict';

  var mod = window.__CdvPurchaseModule || {};
  var api = mod.CdvPurchase || mod.default || mod;
  var cap = window.Capacitor;
  var plugins = cap && cap.Plugins;
  var plugin = plugins && plugins.PurchasePlugin;

  function fail(message) {
    window.__iapNativeBridgeReady = false;
    window.__iapNativeBridgeError = message;
    try { window.dispatchEvent(new Event('cdvpurchase-failed')); } catch (e) {}
  }

  if (!(api && api.store && api.Platform && api.ProductType)) {
    fail('CdvPurchase API bundle is unavailable');
    return;
  }

  /* Capacitor injects native plugin proxies before the web app starts in a
     normal build. If a proxy is not present yet, poll briefly because the
     native bridge can finish registration asynchronously on cold launch. */
  var attempts = 0;
  function exposeWhenReady() {
    cap = window.Capacitor;
    plugins = cap && cap.Plugins;
    plugin = plugins && plugins.PurchasePlugin;
    if (plugin && typeof plugin.init === 'function' && typeof plugin.load === 'function') {
      window.CdvPurchase = api;
      window.CdvPurchaseCapacitor = { installed: true };
      window.__iapNativeBridgeReady = true;
      window.__iapNativeBridgeError = null;
      try { window.dispatchEvent(new Event('cdvpurchase-ready')); } catch (e) {}
      return;
    }
    if (++attempts >= 100) {
      fail('Capacitor PurchasePlugin proxy is unavailable');
      return;
    }
    setTimeout(exposeWhenReady, 100);
  }

  exposeWhenReady();
}());

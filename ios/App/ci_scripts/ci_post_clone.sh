#!/bin/zsh
set -euo pipefail

# Xcode Cloud images provide Homebrew but may not expose Node/npm in PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v npm >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "[ci_post_clone] HATA: Homebrew bulunamadı; Node/npm kurulamadı." >&2
    exit 127
  fi
  echo "[ci_post_clone] Node/npm bulunamadı; Homebrew ile Node kuruluyor."
  brew install node
  export PATH="$(brew --prefix)/bin:$PATH"
fi
command -v node
command -v npm

cd "${CI_PRIMARY_REPOSITORY_PATH:-$PWD}"
echo "[ci_post_clone] Repository: ${CI_PRIMARY_REPOSITORY_PATH:-$PWD}"
echo "[ci_post_clone] Commit: ${CI_COMMIT:-unknown}"

# Dependencies and native plugin references are refreshed in the cloud environment.
npm ci --no-audit --no-fund
npx capacitor-assets generate --ios
npx cap sync ios

# Apply the same production patches used by the signed GitHub build.
python3 scripts/patch-ads.py
python3 scripts/patch-podfile.py
python3 scripts/patch-admob-swift.py
python3 scripts/patch-ios.py

gem install xcodeproj --no-document
ruby scripts/add_privacy_manifest_to_xcodeproj.rb

# Re-run CocoaPods after Podfile and project patches.
cd ios/App
pod install --repo-update

cd "${CI_PRIMARY_REPOSITORY_PATH:-$PWD/../..}"
echo "[ci_post_clone] iOS workspace preparation completed."

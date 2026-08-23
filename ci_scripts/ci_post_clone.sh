#!/bin/zsh
set -euo pipefail

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

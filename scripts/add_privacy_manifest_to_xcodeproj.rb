#!/usr/bin/env ruby
# add_privacy_manifest_to_xcodeproj.rb
# --------------------------------------
# Sadece bir dosyayi diske kopyalamak, Xcode'un onu .ipa icine paketlemesi
# icin YETERLI DEGILDIR -- dosyanin Xcode projesinin (.pbxproj) "Copy Bundle
# Resources" build phase'ine gercek bir referans olarak eklenmesi gerekir.
# Bu script, CocoaPods'un zaten bagimliligi oldugu (ve bu yuzden macOS
# runner'larda `pod install` sonrasi hazir bulunan) `xcodeproj` Ruby gem'ini
# kullanarak bu islemi programatik ve guvenilir sekilde yapar.
#
# Kullanim: ruby scripts/add_privacy_manifest_to_xcodeproj.rb

require 'xcodeproj'

project_path = 'ios/App/App.xcodeproj'
privacy_filename = 'PrivacyInfo.xcprivacy'

unless File.exist?(project_path)
  puts "[add_privacy_manifest] HATA: #{project_path} bulunamadi. 'npx cap add ios' calistirildi mi?"
  exit 1
end

unless File.exist?(File.join('ios/App/App', privacy_filename))
  puts "[add_privacy_manifest] HATA: ios/App/App/#{privacy_filename} bulunamadi. patch-ios.py once calistirilmali."
  exit 1
end

project = Xcodeproj::Project.open(project_path)
app_target = project.targets.find { |t| t.name == 'App' }

if app_target.nil?
  puts "[add_privacy_manifest] HATA: 'App' hedefi (target) bulunamadi."
  exit 1
end

# Ayni dosya zaten ekliyse tekrar eklemeyelim (idempotent).
already_added = app_target.resources_build_phase.files.any? do |bf|
  bf.file_ref && bf.file_ref.display_name == privacy_filename
end

if already_added
  puts "[add_privacy_manifest] PrivacyInfo.xcprivacy zaten projede kayitli, tekrar eklenmedi."
  exit 0
end

# Capacitor'in olusturdugu, Info.plist'i iceren gercek "App" grubunu buluyoruz;
# boylece dosya referansi dogru fiziksel klasore (ios/App/App/) isaret eder.
# Bulunamazsa ana gruba (kok dizin) eklenir.
info_plist_ref = project.files.find { |f| f.display_name == 'Info.plist' }
app_group = info_plist_ref ? info_plist_ref.parent : project.main_group.find_subpath('App', true)

file_ref = app_group.new_reference(privacy_filename)
app_target.add_resources([file_ref])
project.save
puts "[add_privacy_manifest] PrivacyInfo.xcprivacy basariyla 'Copy Bundle Resources' build phase'ine eklendi (grup: #{app_group.hierarchy_path})."


# Ungoogled Chromium

[Ungoogled Chromium](https://github.com/Eloston/ungoogled-chromium/) is an interesting projects that attempts to remove as many google-specific dependencies as possible from Chromium. They support platforms that we don't have to care about (such as Windows), and they're also extremely aggressive in removing and modifying bits of Chromium that the typical Debian user might find excessive.

## Patches

That being said - the Ungoogled Chromium project also has some really useful patches that could help with issues that Debian *does* care about, such as Chromium phoning home (described in [bug #792580](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=792580)). This is a list of the patches that they carry, with a description of why they may or may not be useful to Debian's Chromium packaging efforts.

[last update - 2022-04-13; ordered by their series file](https://github.com/Eloston/ungoogled-chromium/blob/master/patches/series)

 - [ ] ~~core/inox-patchset/0001-fix-building-without-safebrowsing.patch~~

   I think SafeBrowsing is extremely useful. Need to investigate further to see if there are quality non-Google alternatives.

 - [ ] core/inox-patchset/0003-disable-autofill-download-manager.patch

   We likely want some variant of this; however, instead of completely deleting the functionality, we probably want to disable it by default.
   XXX: This patch deletes most of AutofillDownloadManager::StartRequest(), which is called by StartQueryRequest() and StartUploadRequest(); both of which check IsEnabled() before running. IsEnabled() checks for a valid autofill_server_url, so that can just be disabled (hardcoded). Or, kAutofillServerCommunication can be disabled by default. LineageOS does just that in https://github.com/LineageOS/android_external_chromium-webview/blob/master/patches/0004-disable-autofill-server-communication-by-default.patch
  
 - [ ] core/inox-patchset/0005-disable-default-extensions.patch
 - [ ] core/inox-patchset/0007-disable-web-resource-service.patch
 - [ ] core/inox-patchset/0009-disable-google-ipv6-probes.patch
 - [ ] core/inox-patchset/0015-disable-update-pings.patch
 - [ ] core/inox-patchset/0017-disable-new-avatar-menu.patch

 - [ ] ~~core/inox-patchset/0021-disable-rlz.patch~~

   Windows/mac-only patch.

 - [x] core/debian/disable/unrar.patch

   This was taken from debian; it's already included.

 - [ ] core/iridium-browser/safe_browsing-disable-incident-reporting.patch
 - [ ] core/iridium-browser/safe_browsing-disable-reporting-of-safebrowsing-over.patch
 - [ ] core/iridium-browser/all-add-trk-prefixes-to-possibly-evil-connections.patch
 - [ ] core/ungoogled-chromium/disable-crash-reporter.patch
 - [ ] core/ungoogled-chromium/disable-google-host-detection.patch
 - [ ] core/ungoogled-chromium/replace-google-search-engine-with-nosearch.patch
 - [ ] core/ungoogled-chromium/disable-signin.patch
 - [ ] core/ungoogled-chromium/toggle-translation-via-switch.patch
 - [ ] core/ungoogled-chromium/disable-untraceable-urls.patch

   This feature (which does a ping to a "financial" server?) is already disabled on linux in rlz/buildflags/buildflags.gni , but can also be forced off with enable_rlz=false. Thus, windows/mac-only patch.

 - [X] core/disable-web-environment-integrity.patch

   WEI is awful, disable this in debian.

 - [ ] core/ungoogled-chromium/disable-profile-avatar-downloading.patch
 - [ ] core/ungoogled-chromium/disable-gcm.patch
 - [ ] core/ungoogled-chromium/disable-domain-reliability.patch
 - [ ] core/ungoogled-chromium/block-trk-and-subdomains.patch
 - [ ] core/ungoogled-chromium/fix-building-without-one-click-signin.patch
 - [ ] core/ungoogled-chromium/disable-gaia.patch
 - [ ] core/ungoogled-chromium/disable-fonts-googleapis-references.patch
 - [ ] core/ungoogled-chromium/disable-webstore-urls.patch
 - [ ] core/ungoogled-chromium/fix-learn-doubleclick-hsts.patch
 - [ ] core/ungoogled-chromium/disable-webrtc-log-uploader.patch
 - [ ] core/ungoogled-chromium/fix-building-with-prunned-binaries.patch
 - [ ] core/ungoogled-chromium/disable-network-time-tracker.patch
 - [ ] core/ungoogled-chromium/disable-mei-preload.patch
 - [ ] core/ungoogled-chromium/fix-building-without-safebrowsing.patch
 - [ ] core/ungoogled-chromium/remove-unused-preferences-fields.patch
 - [ ] core/ungoogled-chromium/block-requests.patch
 - [ ] core/ungoogled-chromium/disable-privacy-sandbox.patch
 - [ ] core/ungoogled-chromium/doh-changes.patch
 - [ ] core/bromite/disable-fetching-field-trials.patch
 - [ ] extra/inox-patchset/0006-modify-default-prefs.patch
 - [ ] extra/inox-patchset/0008-restore-classic-ntp.patch
 - [ ] extra/inox-patchset/0013-disable-missing-key-warning.patch
 - [ ] extra/inox-patchset/0016-chromium-sandbox-pie.patch
 - [ ] extra/inox-patchset/0018-disable-first-run-behaviour.patch
 - [ ] extra/inox-patchset/0019-disable-battery-status-service.patch

 - [ ] ~~extra/debian/gn/parallel.patch~~
   
   Not part of chromium, only useful for building gn.

 - [x] extra/debian/fixes/connection-message.patch
 - [x] extra/debian/disable/welcome-page.patch
 - [x] extra/debian/disable/google-api-warning.patch

   Already part of debian (and some need to go upstream).

 - [ ] ~~extra/iridium-browser/net-cert-increase-default-key-length-for-newly-gener.patch~~

   Double size of generated RSA keys. We likely don't care about this, and if we do then it should go upstream as a general security improvement.

 - [ ] ~~extra/iridium-browser/mime_util-force-text-x-suse-ymp-to-be-downloaded.patch~~

   Suse-specific patch to keep their YaST installer in check.

 - [ ] ~~extra/iridium-browser/prefs-only-keep-cookies-until-exit.patch~~

   It's too invasive to delete all cookies by default on browser exit. Users can set this themelves in Settings if they want it.

 - [ ] ~~extra/iridium-browser/prefs-always-prompt-for-download-directory-by-defaul.patch~~

   This is a personal preference. I do not like being prompted where to save files.

 - [ ] ~~extra/iridium-browser/updater-disable-auto-update.patch~~

   OSX-specific patch.

 - [ ] extra/iridium-browser/Remove-EV-certificates.patch
 - [ ] extra/iridium-browser/browser-disable-profile-auto-import-on-first-run.patch
 - [ ] extra/ungoogled-chromium/add-components-ungoogled.patch
 - [ ] extra/ungoogled-chromium/add-ungoogled-flag-headers.patch
 - [ ] extra/ungoogled-chromium/disable-formatting-in-omnibox.patch
 - [ ] extra/ungoogled-chromium/add-ipv6-probing-option.patch
 - [ ] extra/ungoogled-chromium/remove-disable-setuid-sandbox-as-bad-flag.patch
 - [ ] extra/ungoogled-chromium/disable-intranet-redirect-detector.patch
 - [ ] extra/ungoogled-chromium/enable-page-saving-on-more-pages.patch
 - [ ] extra/ungoogled-chromium/disable-download-quarantine.patch
 - [ ] extra/ungoogled-chromium/fix-building-without-mdns-and-service-discovery.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-configure-extension-downloading.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-search-engine-collection.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-disable-beforeunload.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-force-punycode-hostnames.patch
 - [ ] extra/ungoogled-chromium/disable-webgl-renderer-info.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-show-avatar-button.patch
 - [ ] extra/ungoogled-chromium/add-suggestions-url-field.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-hide-crashed-bubble.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-scroll-tabs.patch
 - [ ] extra/ungoogled-chromium/enable-paste-and-go-new-tab-button.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-bookmark-bar-ntp.patch
 - [ ] extra/ungoogled-chromium/enable-default-prefetch-privacy-changes.patch
 - [ ] extra/ungoogled-chromium/enable-menu-on-reload-button.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-omnibox-autocomplete-filtering.patch
 - [ ] extra/ungoogled-chromium/disable-dial-repeating-discovery.patch
 - [ ] extra/ungoogled-chromium/remove-uneeded-ui.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-close-window-with-last-tab.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-convert-popups-to-tabs.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-disable-local-history-expiration.patch
 - [ ] extra/ungoogled-chromium/add-extra-channel-info.patch
 - [ ] extra/ungoogled-chromium/prepopulated-search-engines.patch
 - [ ] extra/ungoogled-chromium/fix-distilled-icons.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-clear-data-on-exit.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-tabsearch-button.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-qr-generator.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-grab-handle.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-close-confirmation.patch
 - [ ] extra/ungoogled-chromium/keep-expired-flags.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-custom-ntp.patch
 - [ ] extra/ungoogled-chromium/add-flag-for-tab-hover-cards.patch
 - [ ] extra/ungoogled-chromium/add-flag-to-hide-tab-close-buttons.patch
 - [ ] extra/ungoogled-chromium/disable-remote-optimization-guide.patch
 - [ ] extra/bromite/fingerprinting-flags-client-rects-and-measuretext.patch
 - [ ] extra/bromite/flag-max-connections-per-host.patch
 - [ ] extra/bromite/flag-fingerprinting-canvas-image-data-noise.patch


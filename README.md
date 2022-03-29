
# Debian Chromium packaging

## Chromium Versioning

Chromium upstream releases come in three flavors - stable, beta, and dev. Each release is defined by the first number in the version string (eg, 99.0.4844.74 is release 99). They publish a [calendar](https://chromiumdash.appspot.com/schedule) for releases that show each major release, the date it will transition from dev to beta ("Beta Promotion"), the date it will transition from beta to stable ("Stable Release"), and sometimes when a stable release will receive a bug/security fix update ("Next Refresh").

Debian sid will only ever have a stable release, but experimental may have a beta or dev release. This git repository contains an experimental branch for that.

## Building

If you're updating the Chromium package for a newer upstream version, first create a new changelog entry in debian/changelog with the new version. Then run the following, which will download Chromium's -lite tarball and strip non-free bits from it and create the necessary .orig.tar.xz file. The uscan program will not work on Chromium, which is why you must do this step.
```
./debian/rules get-orig-source
```
Otherwise, just use the existing orig.tar.xz that's already in Debian.

Now unpack `chromium_<version>.orig.tar.xz` and copy the debian/ directory from this git repository into it.
```
tar Jxvf chromium_<version>.orig.tar.xz
cp -ra chromium-git/debian chromium-<version>
```

Finally you can continue with installing build-deps and build it like a normal Debian package.


## Problems Building a Security Update

The most likely problem you're going to run into is a patch not applying due to fuzz.

```
dpkg-source: info: applying disable/devtools-unittests.patch
dpkg-source: info: applying disable/libaom-arm.patch
dpkg-source: info: applying system/icu.patch
patching file net/BUILD.gn
patching file base/BUILD.gn
Hunk #1 FAILED at 56.
Hunk #2 succeeded at 3604 (offset 207 lines).
1 out of 2 hunks FAILED
dpkg-source: info: the patch has fuzz which is not allowed, or is malformed
dpkg-source: info: if patch 'system/icu.patch' is correctly applied by quilt, use 'quilt refresh' to update it
dpkg-source: info: if the file is present in the unpacked source, make sure it is also present in the orig tarball
dpkg-source: info: restoring quilt backup files for system/icu.patch
dpkg-source: error: LC_ALL=C patch -t -F 0 -N -p1 -u -V never -E -b -B .pc/system/icu.patch/ --reject-file=- < chromium-99.0.4844.74/debian/patches/system/icu.patch subprocess returned exit status 1
dpkg-buildpackage: error: dpkg-source --before-build . subprocess returned exit status 2
debuild: fatal error at line 1182:
dpkg-buildpackage -us -uc -ui failed
```

To fix this, just install quilt and run the following:

```
quilt push -f
quilt refresh
```
This will inform you that the patch has been refreshed, and you should be able to continue building. Don't forget to copy the refreshed patch (in the above example, it would be system/icu.patch) into the git repository and commit it, if this is going to be an official Debian upload.


## Problems Building a New Stable Release

Building the first stable release of a new series will likely run into a number of problems. The first is when running `./debian/rules get-orig-source`, the following errors:
```
perl debian/scripts/mk-origtargz ../chromium-100.0.4896.60-lite.tar.xz > ../chromium_100.0.4896.60.files-removed
mk-origtargz warn: No files matched excluded pattern as the last matching glob: *.elf
mk-origtargz warn: No files matched excluded pattern as the last matching glob: *.swf
mk-origtargz warn: No files matched excluded pattern as the last matching glob: *fsevents.node
mk-origtargz warn: No files matched excluded pattern as the last matching glob: third_party/tcmalloc
```
This is more of a warning than an error, but this means that upstream removed the directory `third_party/cmalloc` and it's safe to remove it from debian/copyright's `Files-Excluded:`. However, that directory is probably removed from debian for a reason, and it's worth doing a quick check to ensure the directory wasn't simply renamed. The tcmalloc directory contained `tcmalloc.h`, so I'm doing a quick `find chromium-<version>-lite -name tcmalloc.h` to ensure that the tcmalloc library was *actually* removed before I delete the line in debian/copyright.

```
cd chromium-100.0.4896.60 && ../debian/scripts/check-upstream
prebuilt binary files:
./third_party/rust/libloading/v0_7/crate/tests/nagisa64.dll
./third_party/rust/libloading/v0_7/crate/tests/nagisa32.dll
./third_party/vulkan-deps/vulkan-loader/src/tests/framework/data/binaries/dummy_library_elf_64.dll
./third_party/vulkan-deps/vulkan-loader/src/tests/framework/data/binaries/dummy_library_elf_32.dll
./third_party/devtools-frontend/src/third_party/esbuild/esbuild
make: *** [debian/rules:183: get-orig-source] Error 1
```
This is telling us that upstream is now including additional binaries that we may not have the source for (and therefore we shouldn't distribute). Most of the time, we can simply add lines to debian/copyright's `Files-Excluded:` to simply delete the files (or the directory they're contained in) and the build will still work. That's because upstream's Win32 and Android  builds require those files, but the Linux build does not. In some less common cases, something in the Linux build will depend upon those files, and we'll need to patch a BUILD.gn file and/or modify some source code. That process is described below.

Once debian/copyright has been modified appropriately, `debian/rules get-orig-source` can be run again and will hopefully succeed.







applying patches AND build errors. We are actively trying to drop the number of patches carried by our packaging to make this less likely, but it will always be an issue.
TODO: document checking experimental for patches fixing issues, grabbing upstream/ diffs, vendoring/unbundling, etc.

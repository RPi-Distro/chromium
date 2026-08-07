#!/bin/sh
# init-pre-gen.sh
#
# This script pre-generates a subset of Chromium's build-time-generated
# source files, and packs them into a dedicated orig-source tarball.
#

set -e

deb_arch_to_clang_target()
{
	case "$1" in
		amd64)   echo x86_64-pc-linux-gnu ;;
		arm64)   echo aarch64-linux-gnu ;;
		armhf)   echo arm-linux-gnueabihf ;;
		i386)    echo i386-unknown-linux-gnu ;;
		loong64) echo loongarch64-linux-gnu ;;
		ppc64el) echo powerpc64le-unknown-linux-gnu ;;
	esac
}

if [ ! -f chrome/BUILD.gn ]
then
	echo "error: not inside chromium source tree"
	exit 1
fi
if [ ! -f debian/control ]
then
	echo "error: debian/ subdir not present"
	exit 1
fi

package=$(sed -n 's/^Source: *// p' debian/control)
version=$(dpkg-parsechangelog -S Version)
orig_version=$(echo "$version" | cut -d- -f1)
timestamp=$(cat build/util/LASTCHANGE.committime)
tarball=../${package}_$orig_version.orig-pre-gen.tar.xz

if [ -d pre-gen ]
then
	echo "error: pre-gen/ subdir already exists"
	exit 1
fi
if [ -f $tarball ]
then
	echo "error: pre-gen tarball already exists"
	echo "($tarball)"
	exit 1
fi

arch_list=$(sed -n 's/^Architecture: *// p' debian/control | head -n1)
gcc_ver=$(apt-cache --no-all-versions show gcc | grep '^Depends:' | grep -Po ' gcc-\d\d ' | tr -cd 0-9)
pkg_list=$(for arch in $arch_list; do echo libc6-dev-$arch-cross libgcc-$gcc_ver-dev-$arch-cross; done)
missing_pkg_list=$(for pkg in $pkg_list; do test -f /var/lib/dpkg/info/$pkg.list || echo $pkg; done)

if [ -n "$missing_pkg_list" ]
then
	echo "error: please install the following packages:"
	echo " " $missing_pkg_list
	exit 1
fi
patch=debianization/pre-gen.patch
if ! grep -Fqx $patch .pc/applied-patches
then
	echo "error: $patch is not applied"
	exit 1
fi
if [ ! -f out/Release/args.gn ]
then
	echo "error: source tree is not configured for build"
	exit 1
fi

# Patches for these may not be ready
missing_arch_list=
for arch in loong64 ppc64el
do
	pfx=$(echo $arch | sed 's/loong64/loongarch64/; s/ppc64el/ppc64le/')
	if ! grep -q "^$pfx/" .pc/applied-patches
	then
		echo "note: $arch patches not applied, skipping architecture"
		arch_list=$(echo $arch_list | sed "s/ $arch//")
		missing_arch_list="$missing_arch_list $arch"
	fi
done
test -z "$missing_arch_list" || echo

mkdir pre-gen
python3 debian/deb_pre_gen.py make-lists
echo

# Edit the toolchain.ninja files to remove the static-library dependency
# from the bindgen targets; this dependency is spurious and removing it
# speeds up the generation process significantly
stamp=out/Release/deb-pre-gen-edit.stamp
test -f $stamp || perl -pi.orig-pre-gen \
	-e 'BEGIN {' \
	-e '  open(F, "pre-gen/RULES_ARCH.tmp") or die;' \
	-e '  while (<F>) { chomp; $r{$_}=1; }' \
	-e '  close(F);' \
	-e '}' \
	-e 'if (/^build .*: (\S+) / && $r{$1}) {' \
	-e '  s! obj/\S+/lib\w+\.a( |$)!!;' \
	-e '}' \
	$(find out/Release -type f -name toolchain.ninja)
rm pre-gen/RULES_ARCH.tmp
touch $stamp

target_arch_list=$(cat pre-gen/FILES_ARCH)
target_indep_list=$(cat pre-gen/FILES_INDEP)

export DEB_CR_PRE_GEN=generate

for arch in $arch_list
do
	clang_target=$(deb_arch_to_clang_target $arch)

	echo "Generating arch-dependent files for $arch ($clang_target) ..."

	(cd out/Release && rm -f $target_arch_list)

	DEB_CR_PRE_GEN_ARCH=$arch \
	DEB_CR_PRE_GEN_CLANG=$clang_target \
	ninja -C out/Release $target_arch_list

	echo
done

echo "Generating arch-independent files ..."

(cd out/Release && rm -f $target_indep_list)
ninja -C out/Release $target_indep_list
echo

echo "Generation complete."
echo

# A number of generated files record the full absolute build directory,
# so change that to some standard location for reproducibility
prefix=$(env pwd)
if [ $(echo "$prefix" | tr -cd / | wc -c) -lt 2 ]
then
	echo "warning: build path has too few directory components, skipping normalization of output files"
	echo "(the final tarball should not be publicly released)"
	echo
else
	echo "Normalizing build-path prefix in files ..."
	prefix_qm=$(perl -e 'print quotemeta($ARGV[0])' "$prefix")
	std_prefix=/usr/src/chromium-$orig_version
	find pre-gen -type f -exec perl -pi -e "s!([\"'])$prefix_qm/!\$1$std_prefix/!g" {} +
	echo
	if grep -Flr "$prefix/" pre-gen
	then
		# Probably need to adjust the above "perl -pi" command
		echo "error: build-path prefix is still present in the above file(s)"
		echo "(prefix = \"$prefix/\")"
		exit 1
	fi
fi

cat > pre-gen/README.Debian << END
This tarball/subdirectory contains Chromium source files that, under normal
circumstances, are generated in the course of a (binary) build. Because the
generation process typically requires recent versions of build-dep packages
like bindgen and nodejs, it is prone to failure on Debian stable releases,
where those versions may not be available.

To avoid failed builds due to this, Debian has prepared these files in
advance, so that they can simply be copied into the build tree when needed
rather than the build trying (and failing) to generate them.

Some of the files are specific to an architecture (amd64/**, ppc64el/**
et al.); most are architecture-independent (indep/**). If you have a
fully-built Chromium tree that did not make use of these files, then you
can compare the pre-generated vs. normally-generated sets with e.g.

  $ diff -ru pre-gen/amd64 out/Release
  $ diff -ru pre-gen/indep out/Release

The BUILDINFO file, in deb-buildinfo(5) format, contains details of the
environment in which these files were generated.

To review the implementation of the pre-generated source mechanism, please
see the following files (not in this tarball/subdirectory):

  debian/deb_pre_gen.py
  debian/patches/debianization/pre-gen.patch
  debian/scripts/init-pre-gen.sh

If you do not wish to make use of pre-generated files in your Chromium
build, then simply delete the pre-gen/ subdirectory from the source tree.
(For completeness, you might also want to drop pre-gen.patch from the patch
series.) As long as you have recent-enough build dependencies installed,
the build will not be any worse off.
END

# Record a rudimentary deb-buildinfo(5) file
cat > pre-gen/BUILDINFO << END
Format: 1.0
Source: $package
Architecture: source
Version: $version
Build-Origin: $(perl -ne 'print $1 if /^NAME="(\w+)"/' /etc/os-release)
Build-Architecture: $(dpkg --print-architecture)
Build-Date: $(date -Ru)
Installed-Build-Depends:
$(dpkg-query --show --showformat=' ${binary:Package} (= ${Version}),\n' | sed '$ s/,$//')
END

if [ -n "$missing_arch_list" ]
then
	echo "Architecture-Missing:" $missing_arch_list > pre-gen/INCOMPLETE
	echo "NOTE: The following architecture(s) were skipped:" $missing_arch_list
	echo "(the tarball below should not be publicly released)"
	echo
fi

echo "Making orig-pre-gen tarball ..."

# Use -T1 for reproducibility
XZ_OPT='-6 -T1' tar cJf $tarball \
	--sort=name --owner=0 --group=0 --numeric-owner --mtime=@$timestamp \
	pre-gen

echo
ls -l $tarball

# end init-pre-gen.sh

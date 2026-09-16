#!/bin/sh

set -e

# Prepare chromium's customized node-typescript. Note that "linux-amd64"
# is hardcoded for all Linux archs by upstream (as of v153).
TSPATCH=`pwd`/third_party/node/patches/typescript.patch

usage() {
	echo "Usage: $0 [add|rm] <directory>" 1>&2
	exit 1
}

if [ ! -f "$TSPATCH" ]; then
	echo "Can't find typescript.patch, run this script from the root of a chromium build tree." 1>&2
	exit 2
fi

add_tsc() {
	d="$1"
	parent=`dirname "$d"`

	mkdir -p "$d"
	cp -ra /usr/share/nodejs/typescript/lib/* "$d/"
	cp /usr/share/nodejs/typescript/bin/* "$d/"
	test -f "$parent/package.json" && cp "$parent/package.json" "$parent/package.json.bak" || true
	cp /usr/share/nodejs/typescript/package.json "$parent/"
	V=`tsc --version | sed 's/version //i'`
	dpkg --compare-versions "$V" gt 6.0 && (cd "$d" && patch -p4 < $TSPATCH) || true
}

rm_tsc() {
	d="$1"
	parent=`dirname "$d"`

	rm -rf "$d"
	test -f "$parent/package.json.bak" && mv "$parent/package.json.bak" "$parent/package.json" || true
}

case "$1" in
	add)
		shift
		[ ! -z "$1" ] || usage
		add_tsc "$1"
	;;
	rm)
		shift
		[ ! -z "$1" ] || usage
		rm_tsc "$1"
	;;
	*)
		usage
	;;
esac

exit 0

#!/bin/sh

set -e

test "$#" -eq 1 || {
  echo "Usage: $0 [URL]" 1>&2
  exit 1
}

which elinks >/dev/null || {
  echo 'Error: elinks missing. Do a `sudo apt-get install elinks`.' 1>&2
  exit 1
}

echo
elinks -dump "$1" 2>/dev/null | \
  tr -d '\n' | \
  sed -e 's/[[:space:]]\+/ /g' | \
  sed -ne 's/CVE-/\n- CVE-/pg' | \
  sed -e 's/ on [0-9][0-9].*$/./' | \
  grep -v 'CVE-[0-9\-]\+ exists in the wild' | \
  tail -n +2 | \
  while read ln; do \
    length=`echo $ln | wc -c`; \
    if [ $length -lt 78 ]; then \
      echo "    $ln"; \
    else \
      echo -n "    "; \
      echo $ln|sed 's/.[[:space:]]\+Reported by/.\n      Reported by/'; \
    fi; \
  done
echo

exit 0

#!/bin/sh

set -e

user=""
case "$1" in
  -u)
    shift
    user="$1"
    shift
    ;;
esac

if test -z "${user}"; then
  echo "must pass -u with a gpg id"
  exit 1
fi

cd ..

python setup.py sdist  --formats=bztar,zip

cd dist

./hash-sign.sh -u ${user} *.tar.bz2 *.zip

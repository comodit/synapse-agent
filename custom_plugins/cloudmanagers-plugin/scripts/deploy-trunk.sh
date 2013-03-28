#!/bin/bash
echo "Building comodit-agent cloudmanagers plugin from master"

cd `dirname $0`
cd ..

git checkout master
git pull

NAME="comodit-agent-plugin-cloudmanagers"
VERSION=`git describe --long --match "release*" | awk -F"-" '{print $2}'`
RELEASE=`git describe --long --match "release*" | awk -F"-" '{print $3}'`

./scripts/build-rpm.sh

cp /var/lib/mock/epel-6-i386/result/${NAME}-${VERSION}-${RELEASE}*.noarch.rpm /var/www/html/private/comodit-dev/public/centos/6/i686/
cp /var/lib/mock/epel-6-i386/result/${NAME}-${VERSION}-${RELEASE}*.noarch.rpm /var/www/html/private/comodit-dev/public/centos/6/x86_64/
cp /var/lib/mock/epel-6-i386/result/${NAME}-${VERSION}-${RELEASE}*.src.rpm /var/www/html/private/comodit-dev/public/centos/6/SRPMS/
updaterepo

#!/bin/bash
NAME="synapse-agent"
platforms=(epel-6-i386)

if [ -z $1 ]
then
  VERSION=`git describe --long --match "release*" | awk -F"-" '{print $2}'`
else
  VERSION=$1
fi

if [ -z $2 ]
then
  RELEASE=`git describe --long --match "release*" | awk -F"-" '{print $3}'`
else
  RELEASE=$2
fi

COMMIT=`git describe --long --match "release*" | awk -F"-" '{print $4}'`

cd `dirname $0`
cd ..

# Generate version file
echo "VERSION = \""$VERSION"\"" > synapse/version.py
echo "RELEASE = \""$RELEASE"\"" >> synapse/version.py

sed "s/#VERSION#/${VERSION}/g" ${NAME}.spec.template > ${NAME}.spec
sed -i "s/#RELEASE#/${RELEASE}/g" ${NAME}.spec
sed -i "s/#COMMIT#/${COMMIT}/g" ${NAME}.spec

tar -cvzf $HOME/rpmbuild/SOURCES/${NAME}-${VERSION}-${RELEASE}.tar.gz * \
--exclude .git \
--exclude build \
--exclude dist \
--exclude deb_dist \
--exclude tests \
--exclude devel \
--exclude custom_plugins


rpmbuild -ba ${NAME}.spec

for platform in "${platforms[@]}"
do
    /usr/bin/mock -r ${platform} --rebuild $HOME/rpmbuild/SRPMS/${NAME}-${VERSION}-${RELEASE}*.src.rpm
done

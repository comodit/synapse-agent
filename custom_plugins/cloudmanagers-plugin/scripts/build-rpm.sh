#!/bin/bash
NAME="comodit-agent-plugin-cloudmanagers"
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

cd `dirname $0`
cd ..

sed "s/#VERSION#/${VERSION}/g" ${NAME}.spec.template > $HOME/rpmbuild/SPECS/${NAME}.spec
sed -i "s/#RELEASE#/${RELEASE}/g" $HOME/rpmbuild/SPECS/${NAME}.spec
sed -i "s/#COMMIT#/${COMMIT}/g" $HOME/rpmbuild/SPECS/${NAME}.spec

tar -cvzf $HOME/rpmbuild/SOURCES/${NAME}-${VERSION}-${RELEASE}.tar.gz * \
--exclude *.spec \
--exclude *.template \
--exclude *.sh \
--exclude *.pyc \
--exclude *.pyo \
--exclude *.swp

rpmbuild -ba $HOME/rpmbuild/SPECS/${NAME}.spec

for platform in "${platforms[@]}"
do
    /usr/bin/mock -r ${platform} --rebuild $HOME/rpmbuild/SRPMS/${NAME}-${VERSION}-${RELEASE}*.src.rpm
done

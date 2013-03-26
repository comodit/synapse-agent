Name:           comodit-agent-plugin-cloudmanagers
Version:        #VERSION#
Release:        #RELEASE#%{dist}
Summary:        Cloud managers plugin for comodit-agent

Group:          Development/Languages
License:        MIT
URL:            http://github.com/guardis/synapse-cloudmanagers-plugin
Source0:        %{name}-%{version}-#RELEASE#.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
 
Requires: comodit-agent >= 0.10.dev
Requires: python-rest-client >= 0.3

%description
Cloud managers plugin for the comodit-agent

%prep
%setup -c

# Turn off the brp-python-bytecompile script
# https://fedoraproject.org/wiki/Packaging:Python#Bytecompiling_with_the_correct_python_version
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

%build
 
%install
%{__rm} -rf %{buildroot}

%{__mkdir} -p %{buildroot}/var/lib/comodit-agent/data
%{__mkdir} -p %{buildroot}/usr/share/comodit-agent/plugins/cloudmanagers/templates
%{__mkdir} -p %{buildroot}/var/lib/comodit-agent/plugins/cloudmanagers-plugin
%{__mkdir} -p %{buildroot}/etc/comodit-agent/plugins/

%{__cp} *.py %{buildroot}/var/lib/comodit-agent/plugins/cloudmanagers-plugin
%{__cp} conf/hypervisors.conf %{buildroot}/etc/comodit-agent/plugins
%{__cp} templates/disk.tmpl %{buildroot}/usr/share/comodit-agent/plugins/cloudmanagers/templates
%{__cp} templates/domain.tmpl %{buildroot}/usr/share/comodit-agent/plugins/cloudmanagers/templates

%clean
#%{__rm} -rf %{buildroot}
 
%files
%dir /var/lib/comodit-agent/data
/var/lib/comodit-agent/plugins/cloudmanagers-plugin/*.py
%config(noreplace) /etc/comodit-agent/plugins/cloudmanagers.conf

%changelog
* Fri Mar 08 2013 - michael.vandeborne (at) cetic.be
- Added first changelog log 
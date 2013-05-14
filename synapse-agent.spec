%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%define name synapse-agent

Name:           %{name}
Version:        0
Release:        1%{dist}
Summary:        Host manager

Group:          Development/Languages
License:        MIT
URL:            http://github.com/guardis/%{name}
Source0:        %{name}-%{version}-1.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch

BuildRequires: python-devel
BuildRequires: python-setuptools

Requires: python-pika-ssl == 0.9.13
Requires: python-netifaces >= 0.5
Requires: m2crypto >= 0.15

%description
Dist-agnostic host manager

%prep
%setup -q -c

%build
%{__python} setup.py build

%install
%{__rm} -rf %{buildroot}

%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%{__mkdir} -p %{buildroot}/etc/logrotate.d/
%{__mkdir} -p %{buildroot}/etc/%{name}/ssl/private
%{__mkdir} -p %{buildroot}/etc/%{name}/ssl/certs
%{__mkdir} -p %{buildroot}/etc/%{name}/ssl/csr
%{__mkdir} -p %{buildroot}/etc/init.d
%{__mkdir} -p %{buildroot}/usr/bin
%{__mkdir} -p %{buildroot}/var/lib/%{name}/persistence
%{__mkdir} -p %{buildroot}/var/log/%{name}

%{__cp} conf/%{name}.conf %{buildroot}/etc/%{name}/
%{__cp} conf/permissions.conf %{buildroot}/etc/%{name}/
%{__cp} conf/logger.conf %{buildroot}/etc/%{name}/
%{__cp} bin/%{name} %{buildroot}/usr/bin/
%{__cp} scripts/%{name} %{buildroot}/etc/init.d/

# Remove egg info
%{__rm} -rf %{buildroot}/%{python_sitelib}/synapse*.egg-info

%clean
%{__rm} -rf %{buildroot}

%files

%config(noreplace) /etc/%{name}/%{name}.conf
%config(noreplace) /etc/%{name}/logger.conf
%config(noreplace) /etc/%{name}/permissions.conf
%defattr(644,root,root,-)
%{python_sitelib}/synapse
%defattr(755,root,root,-)
/etc/init.d/%{name}
/usr/bin/%{name}
%dir /etc/logrotate.d
%dir /etc/%{name}/ssl/private
%dir /etc/%{name}/ssl/certs
%dir /etc/%{name}/ssl/csr
%dir /var/lib/%{name}/persistence
%dir /var/log/%{name}
%doc README.md
%doc LICENSE
%doc AUTHORS

%changelog
* Fri Jul 13 2012 - raphael.degiusti (at) gmail.com
- Added first changelog log

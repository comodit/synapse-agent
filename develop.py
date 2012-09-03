#!/usr/bin/env python

import os
import shutil


current_dir = os.path.dirname(os.path.relpath(__file__))


def create_folders(folders):

    for folder in folders:
        try:
            new_folder = os.path.join(current_dir, 'devel', folder)
            print "Creating %s" % new_folder
            os.makedirs(new_folder)
        except OSError:
            continue


def copy_conf_files(files):
    current_conf_folder = os.path.join(current_dir, 'conf')
    new_conf_folder = os.path.join(current_dir, 'devel', 'etc/synapse-agent')

    for fn in files:
        current_conf = os.path.join(current_conf_folder, fn)
        new_conf = os.path.join(new_conf_folder, fn)
        print "Copying %s to %s" % (current_conf, new_conf)
        if os.path.exists(new_conf):
            print "Saving existing %s to %s.save" % (fn, fn)
            shutil.copy(new_conf, new_conf + '.save')
        shutil.copy(current_conf, new_conf)


if __name__ == '__main__':
    folder = ['etc/synapse-agent',
              'etc/synapse-agent/ssl',
              'etc/synapse-agent/ssl/private',
              'etc/synapse-agent/ssl/certs',
              'etc/synapse-agent/ssl/csr',
              'var/lib/synapse-agent/persistence',
              'var/log/synapse-agent',
              'var/run']

    files = ['synapse-agent.conf',
             'logger.conf',
             'permissions.conf']

    create_folders(folder)
    copy_conf_files(files)

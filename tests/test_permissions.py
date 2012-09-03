import re
import os
import unittest

from synapse import permissions


perm_mapping = ['create', 'read', 'update', 'delete', 'ping']


class TestPermissionsProcess(unittest.TestCase):
    def test_fail_if_too_few_sections(self):
        line = "cortex hypervisors *CRUD"
        self.assertRaises(re.error, permissions.process, line)

    def test_fail_if_too_many_sections(self):
        line = "cortex hypervisors * CRUD roger"
        self.assertRaises(re.error, permissions.process, line)

    def test_sanitization(self):
        line = " cortex   hypervisors\t* CRUD\n  \t"
        result = [re.compile('cortex'),
                  re.compile('hypervisors'),
                  re.compile('.*'),
                  set(perm_mapping)]

        test = permissions.process(line)
        test[3] = set(test[3])
        self.assertListEqual(test, result)

    def test_fail_bad_regexp(self):
        line = "cortex hypervisors (((((()) CRUD"
        self.assertRaises(re.error, permissions.process, line)

    def test_bad_permissions_fail(self):
        line = "cortex hypervisors * ARUD"
        self.assertRaises(re.error, permissions.process, line)

    def test_unordered_permissions_success(self):
        line = "cortex hypervisors * DURC"
        # Check no exception is thrown
        permissions.process(line)

    def test_accept_dash_permission(self):
        line = "cortex hypervisors * -"
        # Check no exception is thrown
        permissions.process(line)


class TestPermissionsCheck(unittest.TestCase):

    def setUp(self):
        self.line = "cortex files /etc/httpd/* CRD"

    def test_everything_allowed(self):
        self.line = "* * * CRUD"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_nothing_allowed(self):
        self.line = "* * * -"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_deny_wrong_res_id(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_allow_wildcard_res_id(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/httpd/httpd.conf'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_allow_space_in_res_id(self):
        self.line = """cortex files "/home/user/My Images/*" CRD"""
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/home/user/My Images/test.png'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_allow_wildcard_collection(self):
        self.line = "cortex * * CRD"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'packages'
        res_id = 'httpd'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_wrong_permission(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = '/etc/httpd/httpd.conf'
        action = 'update'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_wrong_collection(self):
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'packages'
        res_id = '/etc/httpd/httpd.conf'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_wrong_user(self):
        perm = permissions.process(self.line)

        user = 'coretekusu'
        collection = 'packages'
        res_id = '/etc/httpd/httpd.conf'
        action = 'read'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)

    def test_if_can_read_then_can_ping(self):
        self.line = "* files * R"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = ''
        action = 'ping'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertTrue(action in perms)

    def test_if_cannot_read_then_cannot_ping(self):
        self.line = "* files * -"
        perm = permissions.process(self.line)

        user = 'cortex'
        collection = 'files'
        res_id = ''
        action = 'ping'
        perms = permissions.check([perm], user, collection, res_id)

        self.assertFalse(action in perms)


class TestPermissionsFile(unittest.TestCase):

    def _get_fp(self, fn):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), fn))

    def test_empty_file_raises_error(self):
        fp = self._get_fp('empty_permissions.conf')
        self.assertRaises(SystemExit, permissions.get, fp)

    def test_absent_file_raises_error(self):
        fp = self._get_fp('nofile.conf')
        self.assertRaises(IOError, permissions.get, fp)

    def test_blank_lines_dont_matter(self):
        fp = self._get_fp('permissions.conf')
        permissions.get(fp)

    def test_lines_order_matter_fail(self):
        fp = self._get_fp('permissions.conf')
        perm_list = permissions.get(fp)

        user = '*'
        collection = 'executables'
        res_id = 'rm -rf /'
        action = 'update'
        perms = permissions.check(perm_list, user, collection, res_id)

        self.assertFalse(action in perms)

    def test_lines_order_matter_success(self):
        fp = self._get_fp('permissions.conf')
        perm_list = permissions.get(fp)

        user = '*'
        collection = 'files'
        res_id = '/etc/hosts'
        action = 'update'
        perms = permissions.check(perm_list, user, collection, res_id)

        self.assertTrue(action in perms)


if __name__ == '__main__':
    unittest.main()

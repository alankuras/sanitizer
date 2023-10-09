import unittest
import sys
import os
import configparser
import json
import logging
from datetime import datetime
from log_file_factory import LogFileFactory, SOURCE
from log_file import LogFile


class TestSanitizerEnv(unittest.TestCase):
    def test_python_version(self):
        self.assertGreater(sys.version_info.major, 2)

    def test_date_parsing(self):
        a = datetime(2008, 11, 22, 12, 0, 0)
        self.assertEqual(a.astimezone().strftime("%Y-%m-%dT%H%z"), '2008-11-22T12+0100')


class TestLogFileFactory(unittest.TestCase):
    def test_logfile_factory_props(self):
        log_factory = LogFileFactory(source=SOURCE.OPENSHIFT)
        self.assertEqual(log_factory._source, SOURCE.OPENSHIFT)
        self.assertEqual(log_factory._logs_location, None)
        self.assertEqual(log_factory._namespaces, [])

    def test_logfile_factory_iterator(self):
        log_factory = LogFileFactory(source=SOURCE.OPENSHIFT, logs_location="/tmp", namespaces=["default"])
        for log_file in log_factory:
            self.assertEqual(type(log_file), LogFile)


class TestLogFile(unittest.TestCase):
    def test_log_file_dump_default_namespace(self):
        logfile_factory = LogFileFactory(source=SOURCE.OPENSHIFT, logs_location="/tmp", namespaces=["default"])
        for logfile in logfile_factory:
            filename = logfile.dump()
            self.assertTrue(os.path.isfile(str(filename)))

    def test_log_file_sanitize_and_dump_default_namespace(self):
        config = configparser.ConfigParser()
        config.read("config.cfg")
        regexes = json.loads(config.get("DEFAULT", "regexes"))
        logfile_factory = LogFileFactory(source=SOURCE.OPENSHIFT, logs_location="/tmp", namespaces=["default"], regexes=regexes)
        for logfile in logfile_factory:
            sanitized_filename = logfile.sanitize_and_dump()
            self.assertTrue(os.path.isfile(str(sanitized_filename)))

    def test_log_file_sanitization_mock(self):
        config = configparser.ConfigParser()
        config.read("config.cfg")
        regexes = json.loads(config.get("DEFAULT", "regexes"))
        logfile = LogFile(
            path="test.log",
            regexes=regexes
        )
        logfile.sanitize_and_dump()
        self.assertTrue(os.path.isfile("test.log.sanitized.gz"))
        # os.unlink("test.log.sanitized.gz")

    def test_adhoc_test(self):
        logger = logging.getLogger()
        logger.setLevel(level=logging.DEBUG)
        config = configparser.ConfigParser()
        config.read("config.cfg")
        regexes = json.loads(config.get("DEFAULT", "regexes"))
        logfile = LogFile(
            path="test.log",
            regexes=regexes
        )
        logfile.content
        print()
        print(("".join(logfile.get_sanitized_content())))


class TestConfigNamespaces(unittest.TestCase):
    def test_config_has_needed_options(self):
        config = configparser.ConfigParser()
        config.read("config.cfg")
        self.assertTrue(config.get("DEFAULT", "namespaces"))
        self.assertTrue(config.get("DEFAULT", "regexes"))

    def test_config_option_parsing(self):
        config = configparser.ConfigParser()
        config.read("config.cfg")
        self.assertTrue(type(json.loads(config.get("DEFAULT", "namespaces"))) is list)
        self.assertTrue(type(json.loads(config.get("DEFAULT", "regexes"))) is list)
        self.assertTrue("default" in json.loads(config.get("DEFAULT", "namespaces")))

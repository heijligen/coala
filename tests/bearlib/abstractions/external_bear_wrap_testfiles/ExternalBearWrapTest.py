import os
import sys
import json
import unittest

from coalib.bearlib.abstractions.ExternalBearWrap import external_bear_wrap
from coalib.results.Diff import Diff
from coalib.results.Result import Result
from coalib.settings.Section import Section
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.settings.FunctionMetadata import FunctionMetadata


def get_testfile_path(name):
    """
    Gets the full path to a testfile inside the same directory.

    :param name: The filename of the testfile to get the full path for.
    :return:     The full path to given testfile name.
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        name)


class ExternalBearWrapComponentTest(unittest.TestCase):

    class Dummy:
        pass

    class TestBear:

        @staticmethod
        def create_arguments():
            return (os.path.join(
                os.path.dirname(__file__),
                "test_external_bear.py"),)

    class WrongArgsBear:

        @staticmethod
        def create_arguments():
            return 1

    def setUp(self):
        self.section = Section("TEST_SECTION")

        self.test_program_path = get_testfile_path("test_external_bear.py")

        self.testfile_path = get_testfile_path("test_file.txt")
        with open(self.testfile_path, mode="r") as fl:
            self.testfile_content = fl.read().splitlines(keepends=True)

    def test_decorator_invalid_parameters(self):
        with self.assertRaises(ValueError) as cm:
            external_bear_wrap("exec", invalid_arg=88)
        self.assertEqual(
            str(cm.exception),
            "Invalid keyword arguments provided: 'invalid_arg'")

    def test_decorator_invalid_parameter_types(self):
        # Provide some invalid severity maps.
        with self.assertRaises(TypeError):
            external_bear_wrap(executable=1337)

    def test_get_executable(self):
        uut = (external_bear_wrap("exec")(self.TestBear))
        self.assertEqual(uut.get_executable(), "exec")

    def test_get_severity(self):
        uut = (external_bear_wrap("exec")(self.Dummy))
        result_major = {'severity': "MAJOR"}
        result_normal = {'severity': "NORMAL"}
        result_info = {'severity': "INFO"}
        result_none = {}
        result_wrong = {'severity': "Info"}

        self.assertEqual(uut.get_severity(result_major),
                         RESULT_SEVERITY.MAJOR)
        self.assertEqual(uut.get_severity(result_normal),
                         RESULT_SEVERITY.NORMAL)
        self.assertEqual(uut.get_severity(result_info),
                         RESULT_SEVERITY.INFO)
        self.assertEqual(uut.get_severity(result_none),
                         RESULT_SEVERITY.NORMAL)
        with self.assertRaises(KeyError):
            uut.get_severity(result_wrong)

    def test_create_arguments_fail(self):
        uut = (external_bear_wrap("exec")(self.Dummy))
        self.assertEqual(uut.create_arguments(), ())

    def test_create_arguments_non_iterable(self):
        uut = (external_bear_wrap("exec")
               (self.WrongArgsBear)
               (self.section, None))
        with self.assertRaises(TypeError):
            res = list(uut.run(self.testfile_path, self.testfile_content))

    def test_invalid_output(self):
        broken_json = json.dumps([{'broken': "JSON"}])[:-1]
        uut = (external_bear_wrap("exec")(self.Dummy)(self.section, None))
        with self.assertRaises(ValueError):
            # Something needs to be done with the result otherwise
            # parse_output will not yield and thus will not raise the ValueError
            list(uut.parse_output(broken_json, "some_file"))

    def test_setting_desc(self):
        uut = (external_bear_wrap("exec",
                                  settings={
                                     "asetting": ("", bool),
                                     "bsetting": ("", bool, True),
                                     "csetting": ("My desc.", bool, False),
                                     "dsetting": ("Another desc", bool),
                                     "esetting": ("", int, None)
                                     })(self.Dummy))
        metadata = uut.get_metadata()
        self.assertEqual(metadata.non_optional_params["asetting"][0],
                         FunctionMetadata.str_nodesc)
        self.assertEqual(metadata.optional_params["bsetting"][0],
                         FunctionMetadata.str_nodesc + " " +
                         FunctionMetadata.str_optional.format(True))
        self.assertEqual(metadata.optional_params["csetting"][0], "My desc." +
                         " " + FunctionMetadata.str_optional.format(False))
        self.assertEqual(metadata.non_optional_params["dsetting"][0],
                         "Another desc")
        self.assertEqual(metadata.optional_params["esetting"][0],
                         FunctionMetadata.str_nodesc + " " +
                         FunctionMetadata.str_optional.format(None))

    def test_optional_settings(self):
        uut = (external_bear_wrap(sys.executable,
                                  settings={"a": ("", bool),
                                            "b": ("", bool, False),
                                            "c": ("", bool, True)})
               (self.TestBear)
               (self.section, None))
        results = list(uut.run(self.testfile_path, self.testfile_content,
                               a=False))
        expected = [
            Result.from_values(
                origin=uut,
                message="This is wrong",
                file=self.testfile_path,
                line=1,
                severity=RESULT_SEVERITY.MAJOR
                ),
            Result.from_values(
                origin=uut,
                message="This is wrong too",
                file=self.testfile_path,
                line=3,
                severity=RESULT_SEVERITY.INFO)]
        self.assertEqual(results, expected)

        results = list(uut.run(self.testfile_path, self.testfile_content,
                               a=True))
        expected = [
            Result.from_values(
                origin=uut,
                message="This is wrong",
                file=self.testfile_path,
                line=1,
                severity=RESULT_SEVERITY.NORMAL
                ),
            Result.from_values(
                origin=uut,
                message="This is wrong too",
                file=self.testfile_path,
                line=3,
                severity=RESULT_SEVERITY.NORMAL)]
        self.assertEqual(results, expected)

    def test_settings(self):
        uut = (external_bear_wrap(sys.executable,
                                  settings={"a": ("", bool),
                                            "b": ("", bool, False),
                                            "c": ("", bool, True)})
               (self.TestBear)
               (self.section, None))
        results = list(uut.run(self.testfile_path, self.testfile_content,
                               a=False, b=True, c=False))
        expected = [
            Result.from_values(
                origin=uut,
                message="This is wrong",
                file=self.testfile_path,
                line=1,
                severity=RESULT_SEVERITY.MAJOR,
                debug_msg="Sample debug message"
                ),
            Result.from_values(
                origin=uut,
                message="Different message",
                file=self.testfile_path,
                line=3,
                severity=RESULT_SEVERITY.INFO)]
        self.assertEqual(results, expected)

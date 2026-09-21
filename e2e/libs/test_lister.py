from robot.api import SuiteVisitor
from robot.api.logger import console


class _TestCollector(SuiteVisitor):

    def __init__(self):
        self.tests = []

    def visit_test(self, test):
        self.tests.append((test.longname, sorted(test.tags)))


class TestLister:
    """Listener printing the selected test cases before the execution starts.

    A listener is used instead of a pre-run modifier because pre-run modifiers run
    before the --include/--exclude/--suite/--test filtering is applied, so they
    cannot report what is actually going to be run.

    Usage: robot --listener test_lister.TestLister ...
    """

    ROBOT_LISTENER_API_VERSION = 3

    def start_suite(self, data, result):
        if data.parent is not None:
            return
        collector = _TestCollector()
        data.visit(collector)
        console(f"\n{'=' * 78}\nSelected {len(collector.tests)} test case(s)\n{'=' * 78}")
        for index, (name, tags) in enumerate(collector.tests, start=1):
            console(f"{index:4d}. {name}    [{', '.join(tags) if tags else '-'}]")
        console("=" * 78)

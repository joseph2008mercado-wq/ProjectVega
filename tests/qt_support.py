"""Drain Qt-owned windows before Python teardown, including deferred dialogs."""

import unittest


class QtTestCase(unittest.TestCase):
    def tearDown(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QApplication
        from shiboken6 import isValid
        app = QApplication.instance()
        if app is not None:
            widgets = app.topLevelWidgets()
            for widget in widgets:
                if isValid(widget):
                    widget.close()
                    widget.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()

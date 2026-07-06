import unittest
import os
import tempfile
import app.security_audit as sa

class TestSecurityAudit(unittest.TestCase):
    def setUp(self):
        # Redirect log file to a temp file
        self.temp_log = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
        self.temp_log.close()
        self.original_path = sa.AUDIT_LOG_PATH
        sa.AUDIT_LOG_PATH = self.temp_log.name

    def tearDown(self):
        sa.AUDIT_LOG_PATH = self.original_path
        if os.path.exists(self.temp_log.name):
            os.remove(self.temp_log.name)

    def test_log_and_retrieve_events(self):
        events_before = sa.get_recent_security_events()
        self.assertEqual(len(events_before), 0)

        # Log some events
        sa.log_security_event("test_event_1", "Description 1", "success", {"meta": "data1"})
        sa.log_security_event("test_event_2", "Description 2", "failure", {"meta": "data2"})

        events_after = sa.get_recent_security_events()
        self.assertEqual(len(events_after), 2)

        # Newest first
        self.assertEqual(events_after[0]["event_type"], "test_event_2")
        self.assertEqual(events_after[0]["status"], "failure")
        self.assertEqual(events_after[0]["metadata"], {"meta": "data2"})

        self.assertEqual(events_after[1]["event_type"], "test_event_1")
        self.assertEqual(events_after[1]["status"], "success")
        self.assertEqual(events_after[1]["metadata"], {"meta": "data1"})
        self.assertTrue(events_after[0].get("entry_hash"))
        self.assertTrue(events_after[1].get("entry_hash"))
        self.assertEqual(events_after[0].get("prev_hash"), events_after[1].get("entry_hash"))

if __name__ == "__main__":
    unittest.main()

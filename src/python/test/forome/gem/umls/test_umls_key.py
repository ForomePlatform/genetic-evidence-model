"""The Studio must not fail silently without a UMLS key.

Without a key every UMLS-backed /api request answers ``needs_key`` (the
browser turns that into the Connect UMLS walkthrough), the key file is the
third lookup source after the environment and .envrc, and POST /api/umls-key
probes the key once, swaps the live client in, and never echoes the key.
"""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from forome.gem.umls import adjudicate_ui as A
from forome.gem.umls.uts_client import NullClient


class TestKeyDiscovery(unittest.TestCase):
    def test_key_file_is_third_source_and_private(self):
        with tempfile.TemporaryDirectory() as d:
            kf = Path(d) / "forome-gem" / "umls_api_key"
            with mock.patch.object(A, "KEY_FILE", kf), \
                 mock.patch.dict(os.environ, {"UMLS_API_KEY": ""}), \
                 mock.patch.object(A.H, "BASE", Path(d)):      # no .envrc here
                self.assertEqual(A.find_api_key(), ("", ""))
                self.assertEqual(A.remember_api_key("  sekrit \n"), kf)
                self.assertEqual(A.find_api_key(), ("sekrit", "key file"))
                self.assertEqual(kf.stat().st_mode & 0o777, 0o600)
                # environment still wins
                with mock.patch.dict(os.environ, {"UMLS_API_KEY": "envkey"}):
                    self.assertEqual(A.find_api_key(), ("envkey", "env"))

    def test_uts_required_respects_local_index(self):
        with mock.patch.multiple(A, UTS_ONLINE=False, LOCAL_INDEX=False):
            self.assertTrue(A.uts_required("/api/search"))
            self.assertTrue(A.uts_required("/api/concept"))
            self.assertFalse(A.uts_required("/api/state"))
            self.assertFalse(A.uts_required("/api/semantictypes"))
        with mock.patch.multiple(A, UTS_ONLINE=False, LOCAL_INDEX=True):
            self.assertFalse(A.uts_required("/api/search"))   # index serves it
            self.assertTrue(A.uts_required("/api/concept"))    # details need UTS
        with mock.patch.multiple(A, UTS_ONLINE=True, LOCAL_INDEX=False):
            self.assertFalse(A.uts_required("/api/search"))

    def test_probe_reports_rejection_without_the_key(self):
        class Resp:
            status_code = 401

        class Boom(Exception):
            response = Resp()

        class Rejecting:
            def __init__(self, key, cache_dir=None):
                pass

            def get_concept(self, cui):
                raise Boom("401 Client Error")

        with mock.patch.object(A, "UTSClient", Rejecting):
            why = A.probe_api_key("hunter2")
        self.assertIn("401", why)
        self.assertNotIn("hunter2", why)


class TestServerWithoutKey(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        kf = Path(self.tmp.name) / "umls_api_key"
        patches = mock.patch.multiple(
            A, client=NullClient(), UTS_ONLINE=False, LOCAL_INDEX=False,
            KEY_SOURCE="", SEARCH_BACKEND="OFFLINE — no UMLS key",
            SEARCH_BACKEND_NOTE="no UMLS_API_KEY in the environment: x",
            KEY_FILE=kf)
        patches.start()
        self.addCleanup(patches.stop)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), A.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        self.base = f"http://127.0.0.1:{srv.server_address[1]}"
        self.kf = kf

    def get(self, path):
        with urlopen(self.base + path) as r:
            return json.loads(r.read())

    def post(self, path, body):
        req = Request(self.base + path, data=json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req) as r:
                return json.loads(r.read())
        except HTTPError as ex:
            return json.loads(ex.read())

    def test_umls_requests_answer_needs_key_then_connect(self):
        for path in ("/api/search?string=gene", "/api/concept?cui=C0017337",
                     "/api/expand?q=gene", "/api/rollup?cui=C0017337"):
            j = self.get(path)
            self.assertTrue(j.get("needs_key"), path)
            self.assertIn("not connected", j["error"])
        self.assertTrue(self.post("/api/rebuild", {}).get("needs_key"))
        # reference data still works offline
        self.assertNotIn("needs_key", self.get("/api/semantictypes"))

        class Live:
            def __init__(self, key, cache_dir=None):
                self.key = key

            def get_concept(self, cui):
                return {"cui": cui}

            def search(self, *a, **k):
                return [{"cui": "C0017337", "name": "Genes"}]

        with mock.patch.object(A, "UTSClient", Live):
            self.assertIn("error", self.post("/api/umls-key", {"key": ""}))
            j = self.post("/api/umls-key", {"key": "k-123", "remember": True})
        self.assertEqual(j.get("ok"), True, j)
        self.assertNotIn("k-123", json.dumps(j))          # never echoed
        self.assertEqual(self.kf.read_text().strip(), "k-123")
        self.assertEqual(j["key_source"], "key file")
        self.assertTrue(A.UTS_ONLINE)
        self.assertEqual(A.SEARCH_BACKEND, "UTS")
        self.assertEqual(A.SEARCH_BACKEND_NOTE, "")
        self.assertEqual(self.get("/api/search?string=gene")["results"][0]["cui"],
                         "C0017337")
        self.assertTrue(self.get("/api/state")["umls"]["connected"])


if __name__ == "__main__":
    unittest.main()

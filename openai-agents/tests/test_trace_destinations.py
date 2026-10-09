import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest


ROOT = Path(__file__).resolve().parents[1]


class TraceDestinations(unittest.TestCase):
    def run_example(self, name: str) -> None:
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_CONNECT(self):
                calls.append(("unexpected_external_connection", self.path, b""))
                self.send_error(502)

            def do_POST(self):
                payload = self.rfile.read(int(self.headers["Content-Length"]))
                calls.append((self.path, self.headers.get("Authorization"), payload))
                if self.path == "/v1/responses":
                    response = {
                        "id": "resp_lens_export_test",
                        "object": "response",
                        "created_at": 1,
                        "status": "completed",
                        "model": "fixture-model",
                        "output": [{
                            "type": "message", "id": "msg_test", "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": "ready", "annotations": []}],
                        }],
                        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                    }
                    body = json.dumps(response).encode()
                    content_type = "application/json"
                elif self.path == "/v1/traces":
                    body = b""
                    content_type = "application/x-protobuf"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            origin = f"http://127.0.0.1:{server.server_port}"
            env = {
                key: value for key, value in os.environ.items()
                if not key.startswith(("OTEL_", "OPENAI_", "LITELLM_", "LENS_", "MOCK_"))
                and key.lower() not in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}
            }
            env.update({
                "OPENAI_API_KEY": "fixture-provider-key",
                "OPENAI_MODEL": "fixture-model",
                "OPENAI_BASE_URL": f"{origin}/v1",
                "LENS_URL": origin,
                "LENS_TRACING_KEY": "fixture-telemetry-key",
                "HTTP_PROXY": origin,
                "HTTPS_PROXY": origin,
                "NO_PROXY": "127.0.0.1,localhost",
            })
            try:
                result = subprocess.run(
                    [sys.executable, str(ROOT / name / "main.py")],
                    env=env, capture_output=True, text=True, timeout=30,
                )
            finally:
                server.shutdown()
                thread.join()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ready", result.stdout)
        model_calls = [call for call in calls if call[0] == "/v1/responses"]
        telemetry = [call for call in calls if call[0] == "/v1/traces"]
        self.assertTrue(model_calls)
        self.assertTrue(telemetry)
        self.assertEqual({call[0] for call in calls}, {"/v1/responses", "/v1/traces"})
        self.assertEqual({call[1] for call in model_calls}, {"Bearer fixture-provider-key"})
        self.assertEqual({call[1] for call in telemetry}, {"Bearer fixture-telemetry-key"})
        names = {
            span.name
            for _, _, payload in telemetry
            for resource in ExportTraceServiceRequest.FromString(payload).resource_spans
            for scope in resource.scope_spans
            for span in scope.spans
        }
        self.assertIn("research_agent", names)
        self.assertIn("research_workflow", names)

    def test_simple_exports_only_to_lens_without_otel_environment(self):
        self.run_example("simple")

    def test_swarm_exports_only_to_lens_without_otel_environment(self):
        self.run_example("swarm")


if __name__ == "__main__":
    unittest.main()

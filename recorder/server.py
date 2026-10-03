import gzip
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from google.protobuf.json_format import MessageToDict, Parse
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

PORT = int(os.environ.get("PORT", "4318"))
TRACES_FILE = Path(os.environ.get("TRACES_FILE", Path(__file__).parent / "traces.jsonl"))


class Handler(BaseHTTPRequestHandler):
    def read_body(self) -> bytes:
        if self.headers.get("Transfer-Encoding") == "chunked":
            body = b""
            while size := int(self.rfile.readline().strip(), 16):
                body += self.rfile.read(size)
                self.rfile.readline()
            self.rfile.readline()
        else:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        return gzip.decompress(body) if self.headers.get("Content-Encoding") == "gzip" else body

    def do_POST(self) -> None:
        if self.path.split("?")[0] != "/v1/traces":
            self.send_response(404)
            self.end_headers()
            return
        export = ExportTraceServiceRequest()
        if "json" in (self.headers.get("Content-Type") or ""):
            Parse(self.read_body(), export)
        else:
            export.ParseFromString(self.read_body())
        print(f"POST /v1/traces auth={self.headers.get('Authorization')!r}", flush=True)
        for resource_spans in export.resource_spans:
            for scope_spans in resource_spans.scope_spans:
                for span in scope_spans.spans:
                    keys = ", ".join(attribute.key for attribute in span.attributes)
                    print(f"  {span.trace_id.hex()[:8]} {span.name!r}: {keys}", flush=True)
        with TRACES_FILE.open("a") as f:
            f.write(json.dumps(MessageToDict(export)) + "\n")
        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        pass


print(f"Recording OTLP traces on http://localhost:{PORT}/v1/traces to {TRACES_FILE}", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()

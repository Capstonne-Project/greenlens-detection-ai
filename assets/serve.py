#!/usr/bin/env python3
"""Run this script to serve the assets folder on localhost:8765
Then Claude can insert images into Google Docs via URL.
Usage: python serve.py
"""

import http.server
import os
import socketserver

os.chdir(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *args):
        pass  # silent


PORT = 8765
print(f"Serving assets at http://localhost:{PORT}")
print("Images available:")
for f in ["results.png", "confusion_matrix.png", "BoxPR_curve.png", "val_batch0_pred.jpg"]:
    print(f"  http://localhost:{PORT}/{f}")
print("\nPress Ctrl+C to stop.")
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()

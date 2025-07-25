#!/usr/bin/env python3
"""
Simple static file server for ARC-AGI-3 Engine Frontend
"""

import http.server
import socketserver
import os
import sys

# Change to the frontend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 3194

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-API-Key')
        super().end_headers()

def main():
    print(f"Starting static file server on port {PORT}")
    print(f"Frontend will be available at: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server")
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped by user")

if __name__ == "__main__":
    main() 
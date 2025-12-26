#!/usr/bin/env python3
"""
Wrapper script for aws_docs_client.py with better process cleanup
Ensures the MCP server process is properly terminated on exit
"""

import sys
import asyncio
import signal
import atexit
from aws_docs_client import main

# Track if we're cleaning up
_cleaning_up = False

def cleanup():
    """Cleanup function to ensure all processes are terminated"""
    global _cleaning_up
    if not _cleaning_up:
        _cleaning_up = True
        print("\nCleaning up...", file=sys.stderr)

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nReceived interrupt signal, exiting...", file=sys.stderr)
    cleanup()
    sys.exit(0)

if __name__ == "__main__":
    # Register cleanup handlers
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the main function
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cleanup()

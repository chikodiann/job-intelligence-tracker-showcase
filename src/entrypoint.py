#!/usr/bin/env python3
"""PyInstaller entrypoint for Ann's Job Intelligence & Application Tracker.

Imports the CLI main function from the job_monitor package so package-relative
imports inside job_monitor execute with proper package context.
"""

import sys
from job_monitor.cli import main

if __name__ == "__main__":
    main()

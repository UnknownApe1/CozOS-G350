#!/usr/bin/env python3
"""Stable CozOS Control Center entry point.

The permanent Ports launcher always starts this file from the active versioned
application directory. Future releases can replace main.py without changing the
Ports launcher itself.
"""
import sys
import control_center_060

if __name__ == '__main__':
    sys.exit(control_center_060.main())

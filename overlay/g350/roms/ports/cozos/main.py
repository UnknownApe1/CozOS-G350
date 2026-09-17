#!/usr/bin/env python3
"""Stable CozOS Control Center entry point.

The one-time Ports bootstrap and permanent Tools launcher both start this file
from the active versioned application directory.
"""
import sys
import control_center_060

if __name__ == '__main__':
    sys.exit(control_center_060.main())

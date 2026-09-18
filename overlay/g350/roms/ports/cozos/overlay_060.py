#!/usr/bin/env python3
"""Run the hardware-tested CozOS overlay helper with the 0.6.2 release identity."""
import sys
import overlay as legacy
legacy.VERSION='0.6.2'
if __name__=='__main__':
    sys.exit(legacy.main())

#!/usr/bin/env python3
"""Convenience launcher: python schedule_optimizer.py --nodes '{...}'"""
import sys

from tdma_planner.cli import main

if __name__ == "__main__":
    sys.exit(main())

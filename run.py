#!/usr/bin/env python3
"""Lanceur de développement : python run.py [--port 8760] [--desktop]"""
import sys
from delivra.server import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

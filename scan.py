#!/usr/bin/env python3
"""Compatibility shim - the scanner lives in scanner/scan.py."""
import pathlib, runpy
runpy.run_path(str(pathlib.Path(__file__).resolve().parent / "scanner" / "scan.py"), run_name="__main__")

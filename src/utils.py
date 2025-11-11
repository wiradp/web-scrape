"""Utility helpers for the web-scrape project."""
import hashlib, logging, json, os

def make_sku_hash(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
source .venv/bin/activate

rm -rf build dist ResearchRadar.spec

pyinstaller \
  --name ResearchRadar \
  --onedir \
  --clean \
  \
  --hidden-import array \
  --hidden-import socket \
  --hidden-import selectors \
  --hidden-import hashlib \
  --hidden-import _hashlib \
  --hidden-import _md5 \
  --hidden-import _sha1 \
  --hidden-import _blake2 \
  \
  --hidden-import streamlit \
  --hidden-import tornado \
  --hidden-import watchdog \
  --hidden-import blinker \
  --hidden-import click \
  --hidden-import rich \
  --hidden-import markdown_it \
  --hidden-import pygments \
  --hidden-import cachetools \
  --hidden-import packaging \
  --hidden-import protobuf \
  --hidden-import pydeck \
  --hidden-import altair \
  \
  --hidden-import dotenv \
  --hidden-import dotenv.main \
  \
  --hidden-import openai \
  --hidden-import httpx \
  --hidden-import httpcore \
  --hidden-import anyio \
  --hidden-import sniffio \
  --hidden-import pydantic \
  --hidden-import pydantic_core \
  --hidden-import distro \
  --hidden-import jiter \
  --hidden-import typing_extensions \
  \
  --hidden-import arxiv \
  --hidden-import feedparser \
  --hidden-import yaml \
  --hidden-import bs4 \
  --hidden-import soupsieve \
  --hidden-import requests \
  --hidden-import urllib3 \
  --hidden-import certifi \
  --hidden-import charset_normalizer \
  --hidden-import idna \
  \
  --collect-all streamlit \
  --collect-all altair \
  --collect-all openai \
  --collect-all arxiv \
  --collect-all feedparser \
  --collect-all dotenv \
  --collect-all bs4 \
  --collect-all requests \
  \
  --copy-metadata streamlit \
  --copy-metadata openai \
  --copy-metadata arxiv \
  --copy-metadata feedparser \
  --copy-metadata python-dotenv \
  --copy-metadata beautifulsoup4 \
  --copy-metadata requests \
  --copy-metadata PyYAML \
  \
  --add-data "app.py:." \
  --add-data "main.py:." \
  --add-data "config:config" \
  --add-data "collectors:collectors" \
  --add-data "core:core" \
  launcher.py

echo ""
echo "Build complete:"
echo "dist/ResearchRadar/ResearchRadar"

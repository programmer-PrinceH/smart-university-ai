"""Plain helper functions shared by the tests."""

import hashlib
import math
import re

import pymupdf

DIM = 256


def fake_embed(text: str) -> list[float]:
    """A deterministic bag-of-words embedding: similar words give similar vectors."""
    vector = [0.0] * DIM
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if len(word) < 3:
            continue
        index = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def make_pdf(pages: list[str]) -> bytes:
    """Build a small real PDF with one text block per page."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 780), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


DB_PAGES = [
    "Normalization is the process of organizing database tables to reduce data "
    "redundancy and improve data integrity. First normal form requires atomic values.",
    "A primary key uniquely identifies each row in a table. A foreign key links a row "
    "in one table to the primary key of another table.",
    "SQL joins combine rows from two tables. An inner join returns only matching rows, "
    "while a left join keeps every row from the left table.",
]

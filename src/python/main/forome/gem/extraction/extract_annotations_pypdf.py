#!/usr/bin/env python3
"""Extract PDF annotations (highlights and text-note callouts) from a PDF.

For each annotation on each page, report:
  - annotation subtype (Highlight, Text, Popup, etc.)
  - page number (1-indexed)
  - the author of the annotation if present
  - the 'Contents' field (what the annotator typed as a note)
  - the quadpoints / rect (location on page)
  - the text actually under the highlight, extracted by coordinates

This matters because a 'Highlight' annotation stores WHERE it is, not WHAT it
covers; the covered text has to be recovered from the page's text content
using the quadpoints.
"""

import sys
import pypdf
from pypdf.generic import ArrayObject, NumberObject


def extract_text_under_quads(page, quadpoints):
    """Given a page and the Highlight's /QuadPoints, extract the text under
    each quad. QuadPoints come in groups of 8: (x1,y1, x2,y2, x3,y3, x4,y4)
    describing the four corners of each rectangle covered by the highlight.

    We use pypdf's visitor-based text extraction to collect only text whose
    position falls inside any quad rectangle.
    """
    if not quadpoints:
        return ""

    # Group quadpoints into (x_min, y_min, x_max, y_max) rects.
    rects = []
    q = [float(v) for v in quadpoints]
    for i in range(0, len(q), 8):
        xs = q[i:i+8:2]
        ys = q[i+1:i+8:2]
        rects.append((min(xs), min(ys), max(xs), max(ys)))

    collected = []

    def visitor(text, cm, tm, fontDict, fontSize):
        # tm is the text matrix; its e,f are the x,y position.
        try:
            x = tm[4]
            y = tm[5]
        except Exception:
            return
        for (xmin, ymin, xmax, ymax) in rects:
            # Allow a small slack in y because tm gives the baseline, not the
            # character box.
            if xmin - 1 <= x <= xmax + 1 and ymin - 4 <= y <= ymax + 4:
                if text and text.strip():
                    collected.append(text)
                return

    try:
        page.extract_text(visitor_text=visitor)
    except Exception as e:
        return f"<extraction error: {e}>"

    return " ".join(collected).strip()


def main(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    print(f"PDF: {pdf_path}")
    print(f"Pages: {len(reader.pages)}")
    print()

    # First pass: find all Popup annotations, keyed by IndirectRef of the
    # Popup object itself. A Highlight often has a /Popup pointer to a
    # Popup annotation which in turn has /Contents (the actual callout text).
    popups_by_ref = {}
    for page_idx, page in enumerate(reader.pages):
        if "/Annots" not in page:
            continue
        for annot_ref in page["/Annots"]:
            annot = annot_ref.get_object()
            subtype = annot.get("/Subtype")
            if subtype == "/Popup":
                popups_by_ref[annot_ref.idnum] = annot

    annot_count = 0
    for page_idx, page in enumerate(reader.pages):
        if "/Annots" not in page:
            continue

        for annot_ref in page["/Annots"]:
            annot = annot_ref.get_object()
            subtype = annot.get("/Subtype", "?")

            # We are most interested in Highlight and Text (callout/sticky).
            # Popups are auxiliary; they'll be read via their parent Highlight.
            if subtype not in ("/Highlight", "/Text", "/Underline",
                               "/Squiggly", "/StrikeOut"):
                continue

            annot_count += 1
            contents = annot.get("/Contents", "")
            author   = annot.get("/T", "")
            quads    = annot.get("/QuadPoints", None)
            rect     = annot.get("/Rect", None)

            # If Highlight has a Popup with Contents, prefer that text
            popup_ref = annot.get("/Popup")
            popup_contents = ""
            if popup_ref is not None:
                try:
                    popup = popup_ref.get_object()
                    popup_contents = popup.get("/Contents", "") or ""
                except Exception:
                    pass

            note_text = contents or popup_contents or ""

            highlighted_text = ""
            if subtype == "/Highlight" and quads is not None:
                highlighted_text = extract_text_under_quads(page, quads)

            print(f"--- Annotation #{annot_count} (page {page_idx+1}) ---")
            print(f"  subtype: {subtype}")
            if author:
                print(f"  author: {author}")
            if note_text:
                print(f"  note/callout: {note_text!r}")
            if highlighted_text:
                print(f"  highlighted text: {highlighted_text!r}")
            elif subtype == "/Text":
                # Sticky note — no highlighted text, but has a location
                if rect:
                    print(f"  location (rect): {list(rect)}")
            print()

    print(f"Total annotations processed: {annot_count}")


if __name__ == "__main__":
    main(sys.argv[1])

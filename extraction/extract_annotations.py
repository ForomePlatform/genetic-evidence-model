#!/usr/bin/env python3
"""Extract PDF highlights and callouts using PyMuPDF.

For each highlight, PyMuPDF can give us the covered text directly via
page.get_textbox(rect) or via the annotation's get_text() method. It also
gives us better handling of Popup-linked callout notes.
"""
import sys
import json
import fitz  # PyMuPDF


def rect_from_quadpoints(quads):
    """Given the 8-float quadpoints, return a fitz.Rect bounding box."""
    if not quads:
        return None
    xs = [quads[i] for i in range(0, len(quads), 2)]
    ys = [quads[i] for i in range(1, len(quads), 2)]
    return fitz.Rect(min(xs), min(ys), max(xs), max(ys))


def main(pdf_path, output_json=None):
    doc = fitz.open(pdf_path)
    results = []

    for page_num, page in enumerate(doc, start=1):
        annot = page.first_annot
        while annot is not None:
            info = annot.info or {}
            atype = annot.type  # (type_id, type_name)
            type_name = atype[1] if atype else "?"
            contents = info.get("content", "") or ""
            author = info.get("title", "") or ""

            entry = {
                "page": page_num,
                "type": type_name,
                "author": author,
                "note": contents.strip() if contents else "",
                "rect": list(annot.rect),
            }

            if type_name == "Highlight":
                # Try multiple extraction strategies and pick the best
                texts = []

                # 1. Quadpoints-based: iterate the vertices in groups of 4
                try:
                    verts = annot.vertices
                    if verts:
                        # vertices come as list of tuples; each highlight quad
                        # uses 4 points
                        for i in range(0, len(verts), 4):
                            quad = verts[i:i+4]
                            if len(quad) == 4:
                                xs = [p[0] for p in quad]
                                ys = [p[1] for p in quad]
                                r = fitz.Rect(min(xs), min(ys),
                                              max(xs), max(ys))
                                t = page.get_textbox(r).strip()
                                if t:
                                    texts.append(t)
                except Exception:
                    pass

                # 2. Fallback: use the annotation rect
                if not texts:
                    try:
                        t = page.get_textbox(annot.rect).strip()
                        if t:
                            texts.append(t)
                    except Exception:
                        pass

                highlighted = " ".join(texts).strip()
                # Clean up the weird line breaks and excess whitespace
                highlighted = " ".join(highlighted.split())
                entry["highlighted_text"] = highlighted

            results.append(entry)
            annot = annot.next

    # Filter out noise: empty highlights with no note
    cleaned = []
    for r in results:
        if r["type"] == "Highlight":
            if not r.get("highlighted_text") and not r.get("note"):
                continue  # skip truly empty
        cleaned.append(r)

    if output_json:
        with open(output_json, "w") as f:
            json.dump(cleaned, f, indent=2)
        print(f"Wrote {len(cleaned)} annotations to {output_json}")
    else:
        for r in cleaned:
            print(f"\n[Page {r['page']}] {r['type']} (author: {r['author']})")
            if r.get("note"):
                print(f"  NOTE: {r['note']}")
            if r.get("highlighted_text"):
                print(f"  TEXT: {r['highlighted_text']}")


if __name__ == "__main__":
    main(sys.argv[1],
         output_json=sys.argv[2] if len(sys.argv) > 2 else None)

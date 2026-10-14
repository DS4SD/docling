# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""Regression tests for JATS table footnotes (table-wrap-foot/fn), issue #4796.

Contract:

* Each nonempty fn directly under table-wrap/table-wrap-foot becomes exactly
  one FOOTNOTE TextItem whose parent is the table, and the table references it
  from TableItem.footnotes in source order.
* A note made of a single non-formula run keeps text, formatting, and hyperlink
  on the wrapper itself.
* A note with several runs or an inline formula uses an empty wrapper whose
  children are the inline TEXT/FORMULA runs.
* A bare p under table-wrap-foot and existing fn-group handling stay unchanged.

All XML below is original synthetic content.
"""

from io import BytesIO

from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    NodeItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.document import Script

from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.document_converter import DocumentConverter


def _convert(body: str) -> DoclingDocument:
    xml = f"""<!DOCTYPE article
PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.2 20190208//EN" "JATS-archivearticle1.dtd">
<article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article">
  <front>
    <article-meta>
      <title-group><article-title>Table Footnote Test</article-title></title-group>
    </article-meta>
  </front>
  <body>
    {body}
  </body>
</article>
"""
    stream = DocumentStream(name="table-footnotes.nxml", stream=BytesIO(xml.encode()))
    converter = DocumentConverter(allowed_formats=[InputFormat.XML_JATS])
    return converter.convert(stream).document


def _table_wrap(
    table_id: str, label: str, caption: str, cell: str, foot: str | None
) -> str:
    foot_xml = f"<table-wrap-foot>{foot}</table-wrap-foot>" if foot is not None else ""
    return f"""
    <table-wrap id="{table_id}">
      <label>{label}</label>
      <caption><p>{caption}</p></caption>
      <table>
        <thead><tr><th>Sample</th><th>Value</th></tr></thead>
        <tbody><tr><td>{cell}</td><td>7</td></tr></tbody>
      </table>
      {foot_xml}
    </table-wrap>
    """


def _footnotes(doc: DoclingDocument, table: TableItem) -> list[TextItem]:
    items = [ref.resolve(doc) for ref in table.footnotes]
    for item in items:
        assert isinstance(item, TextItem)
    return items


def _runs(doc: DoclingDocument, item: NodeItem) -> list[TextItem]:
    """Leaf inline runs under a wrapper, in order (through inline groups)."""
    runs: list[TextItem] = []
    for ref in item.children:
        child = ref.resolve(doc)
        if isinstance(child, TextItem):
            runs.append(child)
        else:
            assert child.label == GroupLabel.INLINE
            runs.extend(_runs(doc, child))
    return runs


def _note_text(doc: DoclingDocument, item: TextItem) -> str:
    """Plain text of a wrapper: its own text, or its inline runs joined."""
    if item.text:
        return item.text
    return " ".join(r.text for r in _runs(doc, item))


def _assert_wrapper(table: TableItem, item: TextItem) -> None:
    assert item.label == DocItemLabel.FOOTNOTE
    assert item.parent is not None
    assert item.parent.cref == table.self_ref


def _all_footnote_texts(doc: DoclingDocument) -> list[TextItem]:
    return [t for t in doc.texts if t.label == DocItemLabel.FOOTNOTE]


def _assert_ordered(haystack: str, *needles: str) -> None:
    positions = []
    for needle in needles:
        assert needle in haystack, f"{needle!r} missing from output:\n{haystack}"
        positions.append(haystack.index(needle))
    assert positions == sorted(positions), f"wrong order {needles} in:\n{haystack}"


SIMPLE = _table_wrap(
    "t1",
    "Table 1",
    "Synthetic yields.",
    "Alpha",
    '<fn id="t1fn1"><p>Values are means of three runs.</p></fn>',
)


def test_simple_table_footnote_is_one_wrapper_owned_by_table():
    doc = _convert(SIMPLE + "<p>Paragraph after table.</p>")

    assert len(doc.tables) == 1
    table = doc.tables[0]
    notes = _footnotes(doc, table)
    assert len(notes) == 1
    _assert_wrapper(table, notes[0])
    assert notes[0].text == "Values are means of three runs."
    assert notes[0].children == []
    assert notes[0].formatting is None
    assert notes[0].hyperlink is None
    # The note is not duplicated elsewhere as another FOOTNOTE text.
    assert [t.self_ref for t in _all_footnote_texts(doc)] == [notes[0].self_ref]


def test_literal_xref_note_stays_one_plain_wrapper():
    foot = (
        '<fn id="x1"><p>From sample [<xref ref-type="bibr" rid="r1">8</xref>],'
        " measured.</p></fn>"
        '<fn id="x2"><p>See <xref ref-type="table-fn" rid="x1">1</xref> now.</p></fn>'
    )
    doc = _convert(_table_wrap("t1", "Table 1", "Xref.", "Alpha", foot))

    table = doc.tables[0]
    notes = _footnotes(doc, table)
    assert [n.text for n in notes] == ["From sample [8], measured.", "See 1 now."]
    for note in notes:
        _assert_wrapper(table, note)
        assert note.children == []
        assert note.formatting is None
        assert note.hyperlink is None

    for out in (doc.export_to_markdown(), doc.export_to_html()):
        assert "From sample [8], measured." in out
        assert "See 1 now." in out
        assert "[ 8 ]" not in out


def test_multiple_notes_and_tables_keep_source_order():
    body = (
        _table_wrap(
            "t1",
            "Table 1",
            "First caption.",
            "Alpha",
            '<fn id="a1"><p>First table note one.</p></fn>'
            '<fn id="a2"><p>First table note two.</p></fn>',
        )
        + "<p>Between tables.</p>"
        + _table_wrap(
            "t2",
            "Table 2",
            "Second caption.",
            "Beta",
            '<fn id="b1"><p>Second table note.</p></fn>',
        )
    )
    doc = _convert(body)

    assert len(doc.tables) == 2
    first, second = doc.tables
    first_notes = _footnotes(doc, first)
    second_notes = _footnotes(doc, second)
    for note in first_notes:
        _assert_wrapper(first, note)
    for note in second_notes:
        _assert_wrapper(second, note)
    assert [n.text for n in first_notes] == [
        "First table note one.",
        "First table note two.",
    ]
    assert [n.text for n in second_notes] == ["Second table note."]

    md = doc.export_to_markdown()
    _assert_ordered(
        md,
        "Table 1 First caption.",
        "Alpha",
        "First table note one.",
        "First table note two.",
        "Between tables.",
        "Table 2 Second caption.",
        "Beta",
        "Second table note.",
    )


def test_labels_and_missing_ids_are_kept_as_note_content():
    foot = (
        "<fn><label>a</label><p>Note without an id.</p></fn>"
        '<fn id="n2"><label>b</label><p>Note with an id.</p></fn>'
    )
    doc = _convert(_table_wrap("t1", "Table 1", "Labels.", "Alpha", foot))

    table = doc.tables[0]
    notes = _footnotes(doc, table)
    assert len(notes) == 2
    for note in notes:
        _assert_wrapper(table, note)
    texts = [_note_text(doc, n) for n in notes]
    assert texts[0].startswith("a")
    assert "Note without an id." in texts[0]
    assert texts[1].startswith("b")
    assert "Note with an id." in texts[1]


def test_styled_linked_and_superscript_runs_are_preserved():
    foot = (
        '<fn id="s1"><p><sup>*</sup>Measured at <italic>room</italic> '
        "<bold>temperature</bold>; see "
        '<ext-link ext-link-type="uri" xlink:href="https://example.org/method">'
        "method</ext-link>.</p></fn>"
    )
    doc = _convert(_table_wrap("t1", "Table 1", "Styles.", "Alpha", foot))

    table = doc.tables[0]
    notes = _footnotes(doc, table)
    assert len(notes) == 1
    wrapper = notes[0]
    _assert_wrapper(table, wrapper)
    assert wrapper.text == ""
    runs = _runs(doc, wrapper)
    assert all(r.label == DocItemLabel.TEXT for r in runs)
    texts = [r.text for r in runs]
    by_text = {r.text: r for r in runs}

    star = by_text["*"].formatting
    assert star is not None and star.script == Script.SUPER
    room = by_text["room"].formatting
    assert room is not None and room.italic
    temperature = by_text["temperature"].formatting
    assert temperature is not None and temperature.bold
    assert str(by_text["method"].hyperlink) == "https://example.org/method"
    assert texts.index("*") < texts.index("room") < texts.index("method")


def test_inline_formula_is_a_formula_run_inside_the_wrapper():
    foot = (
        '<fn id="f1"><p>Error bound is '
        "<inline-formula><tex-math>\\epsilon &lt; 0.5</tex-math></inline-formula>"
        " for all rows.</p></fn>"
    )
    doc = _convert(_table_wrap("t1", "Table 1", "Formula.", "Alpha", foot))

    table = doc.tables[0]
    notes = _footnotes(doc, table)
    assert len(notes) == 1
    wrapper = notes[0]
    _assert_wrapper(table, wrapper)
    assert wrapper.text == ""
    assert [(r.label, r.text) for r in _runs(doc, wrapper)] == [
        (DocItemLabel.TEXT, "Error bound is"),
        (DocItemLabel.FORMULA, "\\epsilon < 0.5"),
        (DocItemLabel.TEXT, "for all rows."),
    ]

    md = doc.export_to_markdown()
    _assert_ordered(md, "Alpha", "Error bound is", "$\\epsilon < 0.5$", "for all rows.")


def test_tables_without_notes_or_with_empty_notes_have_no_footnotes():
    body = (
        _table_wrap("t1", "Table 1", "No foot.", "Alpha", None)
        + _table_wrap(
            "t2", "Table 2", "Empty fn.", "Beta", '<fn id="e1"><p>   </p></fn><fn/>'
        )
        + "<p>Closing paragraph.</p>"
    )
    doc = _convert(body)

    assert len(doc.tables) == 2
    assert all(t.footnotes == [] for t in doc.tables)
    assert _all_footnote_texts(doc) == []
    assert "Closing paragraph." in doc.export_to_markdown()


def test_captions_and_cells_are_not_duplicated():
    doc = _convert(SIMPLE)

    table = doc.tables[0]
    assert len(table.captions) == 1
    captions = [t for t in doc.texts if t.label == DocItemLabel.CAPTION]
    assert [c.text for c in captions] == ["Table 1 Synthetic yields."]
    assert [c.text for c in table.data.table_cells] == ["Sample", "Value", "Alpha", "7"]

    md = doc.export_to_markdown()
    assert md.count("Synthetic yields.") == 1
    assert md.count("Alpha") == 1
    assert md.count("Values are means of three runs.") == 1


def test_existing_fn_group_output_is_unchanged():
    body = (
        SIMPLE
        + """
    <sec>
      <title>Notes</title>
      <fn-group>
        <fn id="g1"><label>1</label><p>Article level note.</p></fn>
      </fn-group>
    </sec>
    """
    )
    doc = _convert(body)

    headings = [t.text for t in doc.texts if t.label == DocItemLabel.SECTION_HEADER]
    assert "Footnotes" in headings
    footnote_lists = [
        g for g in doc.groups if g.label == GroupLabel.LIST and g.name == "footnotes"
    ]
    assert len(footnote_lists) == 1
    list_texts: list[str] = []
    for item_ref in footnote_lists[0].children:
        item = item_ref.resolve(doc)
        list_texts.append(item.text)
        list_texts.extend(r.text for r in _runs(doc, item))
    joined = " ".join(list_texts)
    assert "Article level note." in joined
    # Table notes stay out of the article-level footnote list.
    assert "Values are means of three runs." not in joined

    table = doc.tables[0]
    assert [n.text for n in _footnotes(doc, table)] == [
        "Values are means of three runs."
    ]


def test_bare_paragraph_in_table_wrap_foot_is_unchanged():
    foot = "<p>Bare foot paragraph.</p>"
    doc = _convert(_table_wrap("t1", "Table 1", "Bare.", "Alpha", foot))

    table = doc.tables[0]
    assert table.footnotes == []
    assert _all_footnote_texts(doc) == []
    # Current behavior drops bare table-wrap-foot paragraphs; keep it that way.
    assert all("Bare foot paragraph." not in t.text for t in doc.texts)


def test_json_roundtrip_preserves_footnote_refs_and_runs():
    foot = (
        '<fn id="r1"><p>Plain roundtrip note.</p></fn>'
        '<fn id="r2"><p>Rich <bold>roundtrip</bold> note.</p></fn>'
    )
    doc = _convert(_table_wrap("t1", "Table 1", "Roundtrip.", "Alpha", foot))
    restored = DoclingDocument.model_validate_json(doc.model_dump_json())

    table = restored.tables[0]
    notes = _footnotes(restored, table)
    assert len(notes) == 2
    for note in notes:
        _assert_wrapper(table, note)
    assert notes[0].text == "Plain roundtrip note."
    rich_runs = _runs(restored, notes[1])
    assert [r.text for r in rich_runs] == ["Rich", "roundtrip", "note."]
    bold = rich_runs[1].formatting
    assert bold is not None and bold.bold
    assert restored.export_to_markdown() == doc.export_to_markdown()


def test_markdown_places_notes_after_table_before_following_content():
    foot = (
        '<fn id="m1"><p>Plain markdown note.</p></fn>'
        '<fn id="m2"><p>Note with <italic>emphasis</italic>.</p></fn>'
    )
    doc = _convert(
        _table_wrap("t1", "Table 1", "Markdown.", "Alpha", foot)
        + "<p>Paragraph after table.</p>"
    )

    md = doc.export_to_markdown()
    _assert_ordered(
        md,
        "Table 1 Markdown.",
        "| Alpha",
        "Plain markdown note.",
        "*emphasis*",
        "Paragraph after table.",
    )
    assert md.count("Plain markdown note.") == 1
    assert md.count("emphasis") == 1


def test_html_places_notes_after_table_before_following_content():
    foot = (
        '<fn id="h1"><p>Plain html note.</p></fn>'
        '<fn id="h2"><p>Note with <sup>sup</sup> text.</p></fn>'
    )
    doc = _convert(
        _table_wrap("t1", "Table 1", "Html.", "Alpha", foot)
        + "<p>Paragraph after table.</p>"
    )

    html = doc.export_to_html()
    _assert_ordered(
        html,
        "<table>",
        "Alpha",
        "</table>",
        "Plain html note.",
        "<sup>sup</sup>",
        "Paragraph after table.",
    )
    assert html.count("Plain html note.") == 1
    assert html.count("<sup>sup</sup>") == 1


def _single_note(foot: str) -> tuple[DoclingDocument, TableItem, TextItem]:
    doc = _convert(_table_wrap("t1", "Table 1", "Paragraphs.", "Alpha", foot))
    table = doc.tables[0]
    notes = _footnotes(doc, table)
    assert len(notes) == 1
    _assert_wrapper(table, notes[0])
    return doc, table, notes[0]


def test_paragraphs_in_one_note_keep_a_word_boundary():
    doc, _, note = _single_note('<fn id="p1"><p>alpha</p><p>beta</p></fn>')
    assert note.text == "alpha beta"
    assert note.children == []
    assert "alpha beta" in doc.export_to_markdown()

    # Source line breaks between paragraphs give the same single space.
    _, _, note = _single_note('<fn id="p2"><p>alpha</p>\n  <p>beta</p></fn>')
    assert note.text == "alpha beta"

    # Leading whitespace in the next paragraph is the boundary; add no extra space.
    _, _, note = _single_note('<fn id="p3"><p>alpha</p><p> beta</p></fn>')
    assert note.text == "alpha beta"
    _, _, note = _single_note('<fn id="p4"><p>alpha</p><p>\nbeta</p></fn>')
    assert note.text == "alpha beta"


def test_paragraph_boundary_skips_comments_and_keeps_label_and_tails():
    _, _, note = _single_note(
        '<fn id="c1"><p>Before</p><!-- hidden --><?probe data?><p>after</p></fn>'
    )
    assert note.text == "Before after"

    # The label join is marker behavior and is not changed here.
    _, _, note = _single_note('<fn id="l1"><label>a</label><p>One.</p><p>Two.</p></fn>')
    assert "One. Two." in note.text

    # Text around paragraphs keeps its source order and its existing join.
    _, _, note = _single_note('<fn id="t1">lead <p>alpha</p>mid<p>beta</p> end</fn>')
    assert note.text == "lead alphamid beta end"


def test_paragraph_boundary_keeps_styled_and_formula_runs():
    doc, _, note = _single_note('<fn id="s1"><p><bold>alpha</bold></p><p>beta</p></fn>')
    runs = _runs(doc, note)
    assert [r.text for r in runs] == ["alpha", "beta"]
    assert runs[0].formatting is not None and runs[0].formatting.bold
    assert "**alpha** beta" in doc.export_to_markdown()

    doc, _, note = _single_note(
        '<fn id="f1"><p>x</p>'
        "<p><inline-formula><tex-math>a^2</tex-math></inline-formula></p>"
        "<tex-math>b^2</tex-math><p>y</p></fn>"
    )
    assert [(r.label, r.text) for r in _runs(doc, note)] == [
        (DocItemLabel.TEXT, "x"),
        (DocItemLabel.FORMULA, "a^2"),
        (DocItemLabel.FORMULA, "b^2"),
        (DocItemLabel.TEXT, "y"),
    ]


def test_note_with_only_empty_paragraphs_is_omitted():
    foot = '<fn id="e1"><p> </p><p><!-- c --></p><p>\n</p></fn>'
    doc = _convert(_table_wrap("t1", "Table 1", "Empty.", "Alpha", foot))
    assert doc.tables[0].footnotes == []
    assert _all_footnote_texts(doc) == []

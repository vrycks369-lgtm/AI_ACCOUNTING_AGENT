
import streamlit as st
from datetime import date

st.set_page_config(
    page_title="AI Accounting Agent",
    page_icon="📊",
    layout="wide"
)

st.title("AI Accounting Agent")
st.caption("Accounting intelligence and workflow automation for UAE SMEs")

st.info(
    "Development prototype. Verify accounting, VAT and tax outputs "
    "before using them for business decisions."
)

st.divider()
st.header("Journal Entry Validator")
st.write(
    "Enter a simple or compound journal entry in one table using Account, Debit and Credit. "
    "Total debits must equal total credits."
)

import sqlite3
from pathlib import Path

MASTER_DB_PATH = Path(__file__).with_name("accounting_master.db")

def load_account_options():
    """Load active account suggestions from the SQLite account masterfile."""
    if not MASTER_DB_PATH.exists():
        return []
    try:
        with sqlite3.connect(MASTER_DB_PATH) as conn:
            rows = conn.execute(
                "SELECT account_name FROM accounts WHERE active = 1 ORDER BY account_name COLLATE NOCASE"
            ).fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error:
        return []

account_options = load_account_options()

st.caption(
    "Use one row per account line. Leave unused rows at zero. Ten rows are shown by default."
)
st.markdown(
    """
    <style>
    div[data-testid="stForm"] div[data-testid="stVerticalBlock"] > div {
        gap: 0.25rem;
    }
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
        gap: 0.5rem;
        padding-top: 0.03rem;
        padding-bottom: 0.03rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
line_count = int(st.number_input(
    "Number of journal rows", min_value=1, max_value=100, value=10, step=1,
    key="journal_line_count",
    help="10 rows by default; choose between 1 and 100 account lines as needed.",
))

def normalize_journal_amount(key):
    """Validate amount text while typing, then format it after the edit is committed.

    The field stays plain text during entry so commas/decimal places do not
    move the cursor on every keystroke. On change/commit, valid values are
    normalized to thousands separators and exactly two decimal places.
    """
    raw = str(st.session_state.get(key, "") or "").strip().replace(",", "")
    if raw == "":
        return
    try:
        amount = float(raw)
        if amount < 0:
            st.session_state[key] = ""
        else:
            st.session_state[key] = f"{amount:,.2f}"
    except (ValueError, TypeError):
        # Clear invalid alphabetic input so the field returns to its empty state.
        st.session_state[key] = ""

transaction_date = st.date_input(
    "Transaction date", value=date.today(), key="journal_transaction_date"
)

def clear_transaction_description():
    st.session_state["journal_description"] = ""

def clear_journal_row(row_index):
    st.session_state[f"journal_account_{row_index}"] = None
    st.session_state[f"journal_line_description_{row_index}"] = ""
    st.session_state[f"journal_debit_{row_index}"] = ""
    st.session_state[f"journal_credit_{row_index}"] = ""

description_col, description_clear_col = st.columns([8, 1], gap="small")
with description_col:
    description = st.text_input(
        "Transaction description", value="", key="journal_description"
    )
with description_clear_col:
    st.markdown("<div style='height: 1.85rem'></div>", unsafe_allow_html=True)
    st.button(
        "Clear", key="clear_journal_description",
        on_click=clear_transaction_description, use_container_width=True
    )

# Column headings for the journal table.
# Description uses the same width as Account, as requested.
column_widths = [3.2, 3.2, 1.5, 1.5, 0.9]
header_cols = st.columns(column_widths, gap="small")
for col, heading in zip(
    header_cols,
    ["Account", "Description", "Debit (AED)", "Credit (AED)", "Clear row"],
):
    col.markdown(f"**{heading}**")

journal_lines = []
for i in range(line_count):
    account_col, line_description_col, debit_col, credit_col, clear_row_col = st.columns(
        column_widths, gap="small"
    )
    with account_col:
        account = st.selectbox(
            "Account",
            account_options,
            index=None,
            placeholder="Select or type an account...",
            accept_new_options=True,
            key=f"journal_account_{i}",
            label_visibility="collapsed",
        )
    with line_description_col:
        line_description = st.text_input(
            "Line description", value="", placeholder="Enter description",
            key=f"journal_line_description_{i}",
            label_visibility="collapsed",
        )
    with debit_col:
        debit_text = st.text_input(
            "Debit (AED)", value="", placeholder="Enter amount",
            key=f"journal_debit_{i}",
            on_change=normalize_journal_amount,
            args=(f"journal_debit_{i}",),
            label_visibility="collapsed",
        )
    with credit_col:
        credit_text = st.text_input(
            "Credit (AED)", value="", placeholder="Enter amount",
            key=f"journal_credit_{i}",
            on_change=normalize_journal_amount,
            args=(f"journal_credit_{i}",),
            label_visibility="collapsed",
        )
    with clear_row_col:
        st.button(
            "Clear", key=f"clear_journal_row_{i}",
            on_click=clear_journal_row, args=(i,),
            use_container_width=True,
            help=f"Clear account, debit and credit on row {i + 1}",
        )

    def parse_amount(value, field_name, row_number):
        raw = str(value or "").strip().replace(",", "")
        if raw == "":
            return 0.0
        try:
            amount = float(raw)
            if amount < 0:
                st.error(f"{field_name} on row {row_number} cannot be negative.")
                return None
            return round(amount, 2)
        except ValueError:
            # Invalid text is normally cleared by normalize_journal_amount.
            # Keep rendering quiet; final validation reports any remaining issue.
            return None

    debit_amount = parse_amount(debit_text, "Debit", i + 1)
    credit_amount = parse_amount(credit_text, "Credit", i + 1)
    journal_lines.append({
        "Account": account,
        "Description": line_description,
        "Debit (AED)": debit_amount if debit_amount is not None else 0.0,
        "Credit (AED)": credit_amount if credit_amount is not None else 0.0,
        "_valid_amounts": debit_amount is not None and credit_amount is not None,
    })



def build_journal_pdf(transaction_date, description, journal_lines, total_debits, total_credits):
    """Create a clean, downloadable PDF report for the journal entry."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
        topMargin=16*mm, bottomMargin=16*mm, title="Journal Entry Report"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_LEFT, textColor=colors.HexColor("#243447"), spaceAfter=8))
    styles.add(ParagraphStyle(name="SmallCell", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [
        Paragraph("AI Accounting Agent — Journal Entry Report", styles["ReportTitle"]),
        Paragraph(f"<b>Transaction date:</b> {escape(str(transaction_date))}", styles["BodyText"]),
        Spacer(1, 4),
        Paragraph(f"<b>Transaction description:</b> {escape(str(description or ''))}", styles["BodyText"]),
        Spacer(1, 10),
    ]
    table_data = [["Account", "Line description", "Debit (AED)", "Credit (AED)"]]
    for row in journal_lines:
        if row["Debit (AED)"] > 0 or row["Credit (AED)"] > 0:
            table_data.append([
                Paragraph(escape(str(row.get("Account") or "")), styles["SmallCell"]),
                Paragraph(escape(str(row.get("Description") or "")), styles["SmallCell"]),
                f"{row['Debit (AED)']:,.2f}" if row["Debit (AED)"] else "—",
                f"{row['Credit (AED)']:,.2f}" if row["Credit (AED)"] else "—",
            ])
    if len(table_data) == 1:
        table_data.append(["No journal lines entered", "", "0.00", "0.00"])
    table = Table(table_data, colWidths=[48*mm, 52*mm, 35*mm, 35*mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#243447")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#C7CDD4")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F3F6F9")]),
        ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.extend([table, Spacer(1, 12)])
    totals = Table([
        ["Total Debits", "Total Credits", "Difference"],
        [f"AED {total_debits:,.2f}", f"AED {total_credits:,.2f}", f"AED {total_debits-total_credits:,.2f}"],
    ], colWidths=[56*mm, 56*mm, 58*mm])
    totals.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E8EDF2")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#C7CDD4")),
        ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.extend([totals, Spacer(1, 14), Paragraph(
        "Prototype report for review only. Confirm account selection, source documents, accounting policy, and applicable VAT/tax treatment before posting.",
        styles["Italic"]
    )])
    doc.build(story)
    return buffer.getvalue()


validate_col, pdf_col = st.columns([1, 1])
with validate_col:
    submitted = st.button("Validate Journal Entry", type="primary", use_container_width=True)
with pdf_col:
    pdf_requested = st.button("Create Journal Entry PDF", type="secondary", use_container_width=True)

if submitted:
    # Persist any typed account names that are not already in the manual-derived masterfile.
    typed_accounts = {
        str(row["Account"]).strip()
        for row in journal_lines
        if row["Account"] and str(row["Account"]).strip()
    }
    if typed_accounts and MASTER_DB_PATH.exists():
        try:
            with sqlite3.connect(MASTER_DB_PATH) as conn:
                for account_name in typed_accounts:
                    conn.execute(
                        """INSERT OR IGNORE INTO accounts
                           (account_name, category, source_type, source_document, source_note,
                            occurrences_in_manual, active)
                           VALUES (?, 'Unclassified', 'User-added', NULL,
                                   'Typed by user in Journal Entry Validator; not verified against the manual.', 0, 1)""",
                        (account_name,),
                    )
                conn.commit()
        except sqlite3.Error as exc:
            st.warning(f"Could not update the account masterfile: {exc}")

    st.subheader("Journal Entry Result")
    invalid_amount_rows = [
        idx + 1 for idx, row in enumerate(journal_lines)
        if not row.get("_valid_amounts", True)
    ]
    if invalid_amount_rows:
        st.error(
            "Please correct invalid debit/credit amounts on row(s): "
            + ", ".join(map(str, invalid_amount_rows))
            + "."
        )
    total_debits = round(sum(row["Debit (AED)"] for row in journal_lines), 2)
    total_credits = round(sum(row["Credit (AED)"] for row in journal_lines), 2)
    active_journal_lines = [
        row for row in journal_lines
        if row["Debit (AED)"] > 0 or row["Credit (AED)"] > 0
    ]

    st.write(f"**Date:** {transaction_date}")
    st.write(f"**Description:** {description}")
    if active_journal_lines:
        # Show only user-facing journal columns; keep internal validation flags hidden.
        display_lines = [
            {
                "Account": row["Account"] or "",
                "Description": row["Description"],
                "Debit (AED)": f"{row['Debit (AED)']:,.2f}",
                "Credit (AED)": f"{row['Credit (AED)']:,.2f}",
            }
            for row in active_journal_lines
        ]
        st.table(display_lines)
    else:
        st.warning("Enter at least one debit amount and one credit amount.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Debits", f"AED {total_debits:,.2f}")
    col2.metric("Total Credits", f"AED {total_credits:,.2f}")
    col3.metric("Difference", f"AED {total_debits - total_credits:,.2f}")

    invalid_lines = [
        row for row in active_journal_lines
        if row["Debit (AED)"] > 0 and row["Credit (AED)"] > 0
    ]
    missing_account_lines = [row for row in active_journal_lines if not row["Account"]]
    if invalid_amount_rows:
        st.info("The journal entry was not validated because one or more amounts are invalid.")
    elif missing_account_lines:
        st.error("Select or type an account for every row with a debit or credit amount.")
    elif invalid_lines:
        st.error("Each journal row must have an amount on the debit side OR the credit side, not both.")
    elif total_debits <= 0 or total_credits <= 0:
        st.error("Review required: enter at least one debit and one credit amount.")
    elif total_debits == total_credits:
        st.success("Balanced: total debits equal total credits.")
    else:
        st.error(
            f"Unbalanced by AED {abs(total_debits - total_credits):,.2f}. "
            "Review the amounts before posting."
        )

    st.info(
        "A balanced entry is not necessarily an accurate entry. Confirm the account "
        "selection, transaction evidence, applicable accounting policy and any VAT or "
        "other tax treatment. This validator checks arithmetic and basic line structure; "
        "it does not certify accounting compliance."
    )

if pdf_requested:
    try:
        total_debits_for_pdf = round(sum(row["Debit (AED)"] for row in journal_lines), 2)
        total_credits_for_pdf = round(sum(row["Credit (AED)"] for row in journal_lines), 2)
        pdf_report = build_journal_pdf(
            transaction_date, description, journal_lines,
            total_debits_for_pdf, total_credits_for_pdf
        )
        st.download_button(
            "Download PDF now",
            data=pdf_report,
            file_name=f"Journal_Entry_{transaction_date}.pdf",
            mime="application/pdf",
            key="download_journal_entry_pdf",
            help="Download the journal entry as a PDF. This is separate from validation.",
        )
    except ImportError:
        st.warning(
            "PDF export needs ReportLab. Install it in your project environment with "
            "`python -m pip install reportlab`, then restart the app."
        )

st.divider()
st.caption(
    "Independent development prototype; not an official UAE government "
    "application and not a substitute for professional accounting or tax advice."
)


from knowledge_base import search_manual

st.divider()
st.header("Accounting Manual Search")
st.write(
    "Search Practical Accounting AI Manual "
    "for relevant explanations and page references."
)


def _clear_manual_search():
    """Clear the manual-search input and its previous results."""
    st.session_state["manual_search_question"] = ""
    st.session_state["manual_search_results"] = None
    st.session_state["manual_search_error"] = None


def build_manual_search_pdf(question, results):
    """Create a PDF containing the selected Accounting Manual Search results."""
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title="Accounting Manual Search Results",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ManualReportTitle", parent=styles["Title"],
        textColor=colors.HexColor("#243447"), alignment=0, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="ManualPassage", parent=styles["BodyText"],
        fontSize=9, leading=13, spaceAfter=8,
    ))
    story = [
        Paragraph("AI Accounting Agent — Accounting Manual Search", styles["ManualReportTitle"]),
        Paragraph(f"<b>Search question:</b> {escape(str(question or ''))}", styles["BodyText"]),
        Spacer(1, 10),
    ]
    import re

    for i, result in enumerate(results):
        story.append(Paragraph(
            f"<b>Practical Accounting Explained with AI — page {escape(str(result.get('page', 'N/A')))}</b>",
            styles["Heading2"],
        ))

        # PDF extraction can put blank lines between nearly every source line,
        # which made the exported PDF look like a list of disconnected labels.
        # Normalize all extracted whitespace first, then retain clear section
        # breaks only for numbered headings and recognizable standalone headings.
        raw_text = str(result.get("text", "")).replace("\r\n", "\n").replace("\r", "\n")
        raw_lines = [re.sub(r"\s+", " ", line).strip() for line in raw_text.split("\n")]
        raw_lines = [line for line in raw_lines if line]

        section_pattern = re.compile(
            r"^(?:\d+\.\s+|Worked example:|Account type$|The accounting equation$|"
            r"Assets$|Liabilities$|Equity(?: \(.*?\))?$|Expenses$|Revenue$)",
            re.IGNORECASE,
        )
        paragraphs = []
        current_lines = []
        for line in raw_lines:
            # Keep explanatory content flowing as prose; start a new paragraph
            # only at a genuine numbered section/example heading.
            if current_lines and re.match(r"^\d+\.\s+", line):
                paragraphs.append(" ".join(current_lines))
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            paragraphs.append(" ".join(current_lines))

        for paragraph_text in paragraphs:
            clean_paragraph = re.sub(r"\s+", " ", paragraph_text).strip()
            if clean_paragraph:
                story.append(Paragraph(escape(clean_paragraph), styles["ManualPassage"]))

        if i < len(results) - 1:
            story.append(Spacer(1, 7))
    story.extend([
        Spacer(1, 12),
        Paragraph(
            "For reference only. Confirm the relevant accounting treatment against the full manual, "
            "supporting documents, and applicable accounting policy.",
            styles["Italic"],
        ),
    ])
    doc.build(story)
    return buffer.getvalue()


# Style only the Clear button darker than the main search button.
st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) button {
        background-color: #55585F !important;
        color: #FFFFFF !important;
        border: 1px solid #55585F !important;
    }
    div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) button:hover {
        background-color: #41444A !important;
        border-color: #41444A !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "manual_search_results" not in st.session_state:
    st.session_state["manual_search_results"] = None
if "manual_search_error" not in st.session_state:
    st.session_state["manual_search_error"] = None

question = st.text_input(
    "What accounting topic do you want to research?",
    placeholder="e.g. debit and credit, adjusting entries, depreciation",
    key="manual_search_question",
)

search_col, clear_col = st.columns([4, 1])
with search_col:
    search_clicked = st.button(
        "Search Accounting Manual",
        key="search_manual_button",
        use_container_width=True,
    )
with clear_col:
    st.button(
        "Clear",
        key="clear_manual_search_button",
        on_click=_clear_manual_search,
        use_container_width=True,
        help="Clear the search question and previous results",
    )

if search_clicked:
    if not question.strip():
        st.session_state["manual_search_results"] = None
        st.session_state["manual_search_error"] = "Please enter an accounting question."
    else:
        try:
            st.session_state["manual_search_results"] = search_manual(question)
            st.session_state["manual_search_error"] = None
        except Exception as error:
            st.session_state["manual_search_results"] = None
            st.session_state["manual_search_error"] = f"Could not search the manual: {error}"

if st.session_state["manual_search_error"]:
    st.warning(st.session_state["manual_search_error"])

manual_results = st.session_state["manual_search_results"]
if manual_results is not None:
    if manual_results:
        st.success(f"Found {len(manual_results)} relevant page(s).")

        best_result = manual_results[0]
        st.subheader("Relevant Accounting Guidance")
        st.write(
            "Review the supporting passage below to confirm the treatment "
            "for your transaction. This is a manual search result, not an "
            "AI-generated accounting opinion."
        )
        st.markdown(
            "**Source:** Practical Accounting Explained with AI — "
            f"page {best_result['page']}"
        )
        with st.expander("View supporting manual passage", expanded=True):
            st.write(best_result["text"])

        if len(manual_results) > 1:
            with st.expander("View other matching pages"):
                for result in manual_results[1:]:
                    st.markdown(
                        f"**Page {result['page']} — Match score: {result['score']}**"
                    )
                    st.write(result["text"])

        st.divider()
        include_col, print_col = st.columns([2, 1])
        with include_col:
            include_manual_search = st.checkbox(
                "Include Accounting Manual Search in PDF",
                key="include_manual_search_in_pdf",
                help="Check this to include these search results in the PDF report.",
            )
        with print_col:
            print_manual_pdf = st.button(
                "Print to PDF",
                key="print_manual_search_pdf",
                use_container_width=True,
            )

        if print_manual_pdf:
            if not include_manual_search:
                st.warning("Please check the box to include the Accounting Manual Search results in the PDF.")
            else:
                try:
                    manual_pdf = build_manual_search_pdf(question, manual_results)
                    st.download_button(
                        "Download Accounting Manual PDF",
                        data=manual_pdf,
                        file_name="Accounting_Manual_Search.pdf",
                        mime="application/pdf",
                        key="download_manual_search_pdf",
                    )
                except ImportError:
                    st.warning(
                        "PDF export needs ReportLab. Install it in your project environment with "
                        "`python -m pip install reportlab`, then restart the app."
                    )
    else:
        st.info("No matching pages found. Try different keywords.")

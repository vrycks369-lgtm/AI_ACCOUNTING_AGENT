
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

st.header("Accounting Transaction Assistant")
st.write(
    "Describe a transaction, review the suggested accounting treatment, "
    "and validate a journal entry."
)

transaction_type = st.selectbox(
    "Choose a transaction type",
    [
        "Office supplies paid in cash",
        "Office supplies purchased on credit",
        "Rent paid in cash or bank",
        "Customer pays an outstanding invoice",
        "Sale made on credit",
        "Equipment purchased and paid immediately",
        "Other transaction (manual entry)"
    ]
)

guidance = {
    "Office supplies paid in cash": {
        "debit": "Office Supplies Expense",
        "credit": "Cash",
        "explanation": (
            "Debit the expense to recognize supplies consumed or expensed. "
            "Credit cash because the business's cash balance decreases."
        ),
        "warning": (
            "If the supplies will be held for future use and meet your "
            "accounting policy for an asset, they may need to be recorded "
            "as supplies inventory or a prepaid/current asset instead."
        )
    },
    "Office supplies purchased on credit": {
        "debit": "Office Supplies Expense",
        "credit": "Accounts Payable",
        "explanation": (
            "Debit the expense if the supplies are expensed when acquired. "
            "Credit accounts payable because the supplier has not yet been paid."
        ),
        "warning": (
            "Check whether the supplies should initially be recorded as an "
            "asset. Review the supplier invoice and any recoverable VAT separately."
        )
    },
    "Rent paid in cash or bank": {
        "debit": "Rent Expense",
        "credit": "Bank",
        "explanation": (
            "Rent for the current period is generally debited to rent expense. "
            "Credit bank because the payment reduces the bank balance."
        ),
        "warning": (
            "Rent paid in advance may need to be recorded as prepaid rent and "
            "expensed over the relevant period. Confirm the lease and payment dates."
        )
    },
    "Customer pays an outstanding invoice": {
        "debit": "Bank",
        "credit": "Accounts Receivable",
        "explanation": (
            "Debit bank because money is received. Credit accounts receivable "
            "to reduce the amount the customer owes. Do not record the sale again."
        ),
        "warning": (
            "Match the receipt to the customer invoice and check for bank fees, "
            "short payments or foreign-exchange differences."
        )
    },
    "Sale made on credit": {
        "debit": "Accounts Receivable",
        "credit": "Sales Revenue",
        "explanation": (
            "Debit accounts receivable because the customer owes the business. "
            "Credit sales revenue when the relevant revenue-recognition criteria "
            "are met."
        ),
        "warning": (
            "Confirm that the revenue has been earned. VAT, discounts, returns, "
            "and inventory cost entries may require additional journal lines."
        )
    },
    "Equipment purchased and paid immediately": {
        "debit": "Equipment",
        "credit": "Bank",
        "explanation": (
            "Equipment that qualifies for capitalization is debited to an asset. "
            "Credit bank because the payment reduces the bank balance."
        ),
        "warning": (
            "Confirm the capitalization threshold, business use, invoice details "
            "and useful life. Depreciation may be required. VAT treatment is "
            "not determined by this entry."
        )
    },
    "Other transaction (manual entry)": {
        "debit": "Select the appropriate debit account",
        "credit": "Select the appropriate credit account",
        "explanation": (
            "The correct treatment depends on the underlying transaction, "
            "supporting documents, accounting policy and applicable standards."
        ),
        "warning": (
            "Do not post the entry until the accounts and accounting treatment "
            "have been reviewed."
        )
    }
}

suggestion = guidance[transaction_type]

st.subheader("Accounting Guidance")
st.write("**Suggested debit:**", suggestion["debit"])
st.write("**Suggested credit:**", suggestion["credit"])
st.write("**Why this treatment may apply:**", suggestion["explanation"])
st.warning(suggestion["warning"])

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
    "Number of journal rows", min_value=10, max_value=20, value=10, step=1,
    key="journal_line_count",
    help="10 rows by default; increase if the transaction needs more account lines.",
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
        "Transaction description", value=transaction_type, key="journal_description"
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

submitted = st.button("Validate Journal Entry", type="primary")

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
    """Clear the manual-search input before Streamlit reruns the app."""
    st.session_state["manual_search_question"] = ""


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
        st.warning("Please enter an accounting question.")
    else:
        try:
            results = search_manual(question)

            if results:
                st.success(f"Found {len(results)} relevant page(s).")

                # Lead with the strongest matching passage and its page reference.
                best_result = results[0]
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

                if len(results) > 1:
                    with st.expander("View other matching pages"):
                        for result in results[1:]:
                            st.markdown(
                                f"**Page {result['page']} — Match score: {result['score']}**"
                            )
                            st.write(result["text"])
            else:
                st.info(
                    "No matching pages found. Try different keywords."
                )

        except Exception as error:
            st.error(f"Could not search the manual: {error}")

AI ACCOUNTING AGENT — ACCOUNT MASTERFILE
========================================

Files:
- accounting_master.db: SQLite database used by the app.
- account_masterfile.xlsx: editable/reviewable account masterfile.
- account_masterfile.csv: portable flat-file copy.
- app.py: updated Streamlit app that reads account suggestions from SQLite.

Extraction:
- Account phrases were included only when an exact phrase was found in the supplied PDF:
  Practical_Accounting_Explained_with_AI_Complete_Manual.pdf
- The masterfile currently contains 72 phrase matches after deduplication.
- Phrase occurrence counts indicate how often the exact phrase appears in extracted PDF text.
- Suggested categories are classifications for review, not authoritative classifications supplied by the manual.
- This is a curated extraction of candidate account names, not a guarantee that every account-like phrase in the 149-page manual has been captured. Review the masterfile against the manual before treating it as exhaustive.

App behavior:
- Account rows start blank.
- Users can select a suggestion from SQLite or type a different account name.
- When the user validates a journal entry, typed account names are saved to SQLite as "User-added" unless already present.
- User-added names are clearly marked as not verified against the manual.
- Keep accounting_master.db in the same folder as app.py.

Install:
1. Back up your current app.py.
2. Copy this app.py and accounting_master.db into your project folder:
   C:\Users\Victor Rick\Documents\AI_ACCOUNTING_AGENT
3. Keep app.py and accounting_master.db in the same folder.
4. Restart Streamlit or refresh the browser.
5. The CSV/XLSX masterfile copies are for review and editing; edits to those files do not automatically update SQLite.

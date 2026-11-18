:doc:`/index`

.. _qluster_label:

DeepDiff and Qluster
====================

DeepDiff is maintained by the team behind `Qluster <https://qluster.ai>`__. DeepDiff compares, searches and hashes
Python objects. Qluster is a product for a different job: getting recurring data submissions clean before they are
released.


What Qluster does
-----------------

Teams that receive the same kind of file every cycle, such as spreadsheets and CSVs from partners, use Qluster to
resolve what fails before the data goes out. Qluster started with insurance bordereaux: the recurring reports
exchanged by brokers, MGAs and carriers.

- **Senders keep their workflow.** Partners email files as they do today, or work in Qluster directly.
- **Agents do the setup work.** AI agents map each sender's columns to your schema, write and test rules, and
  propose fixes for rows that fail.
- **Rules check the data.** Versioned rules check every row, so the same file gets the same answer every cycle.
  Rows that fail are quarantined with the reason they failed.
- **People control release.** Only your team approves fixes and signs off what goes out, and every change is logged.
- **Fixes are reused.** Approved fixes become mappings and rules, so the next file needs less manual work.

Each failed submission follows the same path: notice what failed, understand why, fix the data or adjust the rule
parameters, reprocess only what changed, and confirm the result before release.


When Qluster fits
-----------------

Qluster is likely a fit when:

- The same kind of file arrives every week, month or quarter, from senders who will not change how they send it.
- Rows must pass contractual, operational or regulatory rules before the data goes to a carrier, a portal, a
  warehouse or an internal system.
- Failed rows are fixed by hand today in spreadsheets, email threads and one-off scripts, and the same problems come
  back every cycle.
- You need a record of what was changed, why, and who approved it.

Qluster is not the right tool when:

- You need to compare two objects or files, once or in tests. Use :doc:`/diff`, or the :doc:`/commandline` for files.
- You want to validate data inside your own code. A schema library such as pydantic or pandera is enough.
- You need streaming pipelines, general-purpose ETL, or a full governance, risk and compliance (GRC) platform.


For developers
--------------

- `qluster-sdk <https://github.com/qlustered/qluster-sdk>`__ is open source. Install it with
  ``pip install qluster_sdk`` and write custom validation, correction and enrichment rules as Python classes with
  typed parameters.
- `qctl <https://github.com/qlustered/qctl>`__ is the Qluster command-line interface for tables, rules, jobs, alerts
  and reviews. ``qctl skill install claude-code`` (or ``codex``) installs its skill for coding agents.


Questions
---------

**I already use DeepDiff to compare monthly files. Do I need Qluster?**
    Not to find the differences: DeepDiff does that. Qluster is for what comes after, when rows break your rules and
    someone has to work out why, fix them, recheck them and sign off before the data is sent on.

**Does my team or my partners have to change how files are sent?**
    No. Partners can keep emailing files. Qluster takes them as they arrive.

**Does the AI change data on its own?**
    No. Agents propose fixes and draft rules. People approve fixes and sign off releases, and every change is logged.

**Is it only for insurance?**
    Qluster started with insurance bordereaux. The same workflow applies to other recurring, file-based submissions
    where rows have to pass rules before release, such as partner feeds and regulatory reports.

To see Qluster on your own files, `book a demo <https://qluster.ai/contact-us>`__.

Back to :doc:`/index`

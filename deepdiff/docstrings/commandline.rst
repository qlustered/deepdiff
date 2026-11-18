:doc:`/index`

Command Line
============

`New in DeepDiff 5.2.0`

DeepDiff provides commandline interface to a subset of functionality that it provides through its Python API.

The commands are:

- :ref:`deep_diff_command`
- :ref:`deep_grep_command`
- :ref:`deep_extract_command`
- :ref:`deep_patch_command`

.. seealso::
    For CSV or spreadsheet submissions that arrive every cycle and have rows to fix before release, see
    :doc:`/qluster`.


.. _deep_diff_command:

deep diff command
-----------------

Run 

.. code:: bash

  $ deep diff

to get the options:

.. code-block:: bash

    $ deep diff --help
    Usage: deep diff [OPTIONS] T1 T2

      Deep Diff Commandline

      Deep Difference of content in files.
      It can read csv, tsv, json, yaml, and toml files.

      T1 and T2 are the path to the files to be compared with each other.

    Options:
      --cutoff-distance-for-pairs FLOAT
                                      [default: 0.3]
      --cutoff-intersection-for-pairs FLOAT
                                      [default: 0.7]
      --cache-size INTEGER            [default: 0]
      --cache-tuning-sample-size INTEGER
                                      [default: 0]
      --cache-purge-level INTEGER RANGE
                                      [default: 1]
      --create-patch                  [default: False]
      --exclude-paths TEXT
      --exclude-regex-paths TEXT
      --math-epsilon DECIMAL
      --get-deep-distance             [default: False]
      --group-by TEXT
      --ignore-order                  [default: False]
      --ignore-string-type-changes    [default: False]
      --ignore-numeric-type-changes   [default: False]
      --ignore-type-subclasses        [default: False]
      --ignore-string-case            [default: False]
      --ignore-nan-inequality         [default: False]
      --include-private-variables     [default: False]
      --log-frequency-in-sec INTEGER  [default: 0]
      --max-passes INTEGER            [default: 10000000]
      --max_diffs INTEGER
      --number-format-notation [f|e]  [default: f]
      --progress-logger [info|error]  [default: info]
      --report-repetition             [default: False]
      --significant-digits INTEGER
      --truncate-datetime [second|minute|hour|day]
      --verbose-level INTEGER RANGE   [default: 1]
      --view [-|colored|colored_compact]
                                      [default: -]
                                      Format for displaying differences.
      --help                          Show this message and exit.


Example usage:

Let's imagine we have t1.csv and t2.csv:

.. csv-table:: t1.csv
   :file: ../tests/fixtures/t1.csv
   :header-rows: 1


.. csv-table:: t2.csv
   :file: ../tests/fixtures/t2.csv
   :header-rows: 1

We can run:

.. code-block:: bash

    $ deep diff t1.csv t2.csv --ignore-order
    {'values_changed': {"root[2]['zip']": {'new_value': 90002, 'old_value': 90001}}}

As you can see here the path to the item that is being changed is `root[2]['zip']` which is ok but
what if we assume last names are unique and group by last_name?

.. code-block:: bash

    $ deep diff t1.csv t2.csv --ignore-order --group-by last_name
    { 'values_changed': { "root['Molotov']['zip']": { 'new_value': 90002,
                                                      'old_value': 90001}}}

The path is perhaps more readable now: `root['Molotov']['zip']`. It is more clear that the zip code of Molotov has changed.

.. Note::
    The parameters in the deep diff commandline are a subset of those in :ref:`deepdiff_label` 's Python API.

To output in a specific format, for example the colored compact view (see :doc:`colored_view` for output details):

.. code-block:: bash

    $ deep diff t1.json t2.json --view colored_compact


.. _deep_grep_command:

deep grep command
-----------------

Run 

.. code:: bash

  $ deep grep

to get the options:

.. code-block:: bash

    $ deep grep --help
    Usage: deep grep [OPTIONS] ITEM PATH

      Deep Grep Commandline

      Grep through the contents of a file and find the path to the item.
      It can read csv, tsv, json, yaml, and toml files.

    Options:
      -i, --ignore-case              [default: False]
      --exact-match                  [default: False]
      --exclude-paths TEXT
      --exclude-regex-paths TEXT
      --verbose-level INTEGER RANGE  [default: 1]
      --help                         Show this message and exit.


.. csv-table:: t1.csv
   :file: ../tests/fixtures/t1.csv
   :header-rows: 1

.. code-block:: bash

    $ deep grep --ignore-case james t1.csv
    {'matched_values': ["root[2]['first_name']"]}


.. _deep_extract_command:

deep extract command
--------------------

Run

.. code:: bash

  $ deep extract

to get the options:

.. code-block:: bash

    $ deep extract --help
    Usage: deep extract [OPTIONS] PATH_INSIDE PATH

      Deep Extract Commandline

      Extract an item from a file based on the path that is passed. It can read
      csv, tsv, json, yaml, and toml files.

    Options:
      --help  Show this message and exit.

.. csv-table:: t1.csv
   :file: ../tests/fixtures/t1.csv
   :header-rows: 1

.. code-block:: bash

    $ deep extract "root[2]['first_name']" t1.csv
    'James'


.. _deep_patch_command:

deep patch command
------------------

Run

.. code:: bash

  $ deep patch --help

to get the options:

.. code-block:: text

    $ deep patch --help
    Usage: deep patch [OPTIONS] PATH DELTA_PATH

      Deep Patch Commandline

      Patches a file based on the information in a delta file. The delta file
      can be created by the deep diff command and passing the --create-patch
      argument.

      Deep Patch is similar to Linux's patch command. The difference is that it
      is made for patching data. It can read csv, tsv, json, yaml, and toml
      files.

    Options:
      -b, --backup    [default: False]
      --raise-errors  [default: False]
      --help          Show this message and exit.

Imagine if we have the following files:


.. csv-table:: t1.csv
   :file: ../tests/fixtures/t1.csv
   :header-rows: 1

.. csv-table:: t2.csv
   :file: ../tests/fixtures/t2.csv
   :header-rows: 1


First we need to create a "delta" file which represents the difference between the 2 files.

.. code-block:: bash

    $ deep diff t1.csv t2.csv --ignore-order
    {'values_changed': {"root[2]['zip']": {'new_value': 90002, 'old_value': 90001}}}

We create the delta by using the deep diff command and passing the `--create-patch` argument.
However since we are using `--ignore-order`, `deep diff` will ask us to also use `--report-repetition`:

.. code-block:: bash

    deep diff t1.csv t2.csv --ignore-order --report-repetition --create-patch
    =}values_changed}root[2]['zip']}    new_valueJ_sss.% 

Note that the delta is not human readable. It is meant for us to pass it into a file:

.. code-block:: bash

    deep diff t1.csv t2.csv --ignore-order --report-repetition --create-patch > patch1.pickle

Now this delta file is ready to be applied by the `deep patch` command to any json, csv, toml or yaml file!
It is expecting the structure of the file to be similar to the one in the csv file though.

Let's look at this yaml file:

`another.yaml`

.. code-block:: yaml

    ---
    -
        first_name: Joe
        last_name: Nobody
        zip: 90011
    -
        first_name: Jack
        last_name: Doit
        zip: 22222
    -
        first_name: Sara
        last_name: Stanley
        zip: 11111

All that our delta knows is that `root[2]['zip']` has changed to `90002`.

Let's apply the delta:

.. code-block:: bash

    deep patch --backup another.yaml patch1.pickle --raise-errors

And looking at the `another.yaml` file, the zip code is indeed updated!

.. code-block:: yaml

    - first_name: Joe
      last_name: Nobody
      zip: 90011
    - first_name: Jack
      last_name: Doit
      zip: 22222
    - first_name: Sara
      last_name: Stanley
      zip: 90002

As you can see the formatting of the yaml file is changed.
This is due to the fact that DeepDiff loads the file into a Python dictionary, modifies it and then writes it back to disk.
During this operation, the file loses its original formatting.

.. note::
    The deep patch command only provides a subset of what DeepDiff's :ref:`delta_label`'s Python API provides.
    The deep patch command is minimalistic and is designed to have a similar interface to Linux's patch command
    rather than DeepDiff's :ref:`delta_label`.

Back to :doc:`/index`

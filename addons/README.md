# Add-ons

A more comprehensive guide to addons can be found in the wiki: https://github.com/bohning/usdb_syncer/wiki/Creating-custom-addons

You can write your own Python add-ons to extend or modify the syncer's functionality at
runtime. An add-on is either a Python module, or a zip file containing one or more Python modules.
Example:

```txt
.
└── addons/
    ├── addon1.zip/
    │   ├── addon1/
    │   │   ├── __init__.py
    │   │   ├── file1.py
    │   │   └── file2.py
    │   └── addon2/
    │       ├── __init__.py
    │       ├── file1.py
    │       └── file2.py
    ├── addon3/
    │   ├── __init__.py
    │   ├── file1.py
    │   └── file2.py
    └── addon4.py
```

There are two main ways to add or change behaviour:

1. Using the hook system. This method is less versatile, because you can only react to
   a number of predefined events. However, this approach is much more robust, as
   development on the syncer can take care not to break this API. Examples for how to use
   the hook system can be found in `demo.py`.
   A list of hooks and their features can be found in the wiki.
2. Overwrite existing functions, classes, etc. (also known as monkey patching). This
   lets you make any thinkable change, but is discouraged, because your add-on will regularly
   break when there is a change in the syncer itself.

Once you have written the code, place it in the user data directory under `addons`.
This is the same folder that also contains the log file, so you can use the menu in
the syncer to open that directory.

Feel free to submit a new hook if your use case requires it.

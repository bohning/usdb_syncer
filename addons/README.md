# Add-ons

You can write your own Python add-ons to extend or modify the syncer's functionality at
runtime. An add-on is just a Python package or module that is automatically imported at startup.

There are two main ways to add or change behaviour:

1. Overwrite existing functions, classes, etc. (also known as monkey patching). This
   lets you make any thinkable change, but is discouraged, because your add-on will regularly
   break when there is a change in the syncer itself.
2. Using the hook system. This method is less versatile, because you can only react to
   a number of predefined events. However, this approach is much more robust, as
   development on the syncer can take care not to break this API.

Once you have written the code, place it in the user data directory under `addons`.
This is the same folder that also contains the log file, so you can use the menu in
the syncer to open that directory.

Feel free to submit a new hook if your use case requires it.

##################
SQuaSH API scripts
##################

Utiliy sripts for the SQuaSH API


Dump and restore InfluxDB databases
===================================

Migrate InfluxDB data from one instance to another using the ``dump.sh`` and ``restore.sh`` scripts.

.. note::

  It is important to set the correct kubectl context before running each
  script.

.. code::

  kubectl config use-context <context of the source InfluxDB instance>
  dump.sh <namespace> <database>

Use the output directory of the dump command as input for the restore command:

.. code::

  kubectl config use-context <context of the source InfluxDB instance>
  restore.sh <namespace> <input dir>


Copy Chronograf and Kapacitor context databases
===============================================

The Chronograf context database stores Chronograf dashboard definitions, Chronograf users and Chronograf organizations data.
The Kapacitor context database stores the Alert Rules and TICKscripts.

Use the ``contextdb.sh`` script to copy the context database files from a running Chronograf or Kapacitor instance.

.. code::

  contextdb.sh <namespace>

To migrate these databases to another instance, you can restore these files and restart the corresponding pods.

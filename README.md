# jbosscli.py

Sample class that uses JBoss EAP server's REST API to access various settings.

## Sample execution

```
$ ./jbosscli.py
Connected to http://localhost:9990/management
Server: WildFly Full (10.0.0.Final)
JBoss is running.
HEAP: used:116916976 max:477626368
THREAD: current:311 peak:311
# get_mdbs_by_deployment()
+-----------------------+---------------+------------+--------------+
| Message Driven Bean   |   Invocations | Delivery   |   Pool Count |
+=======================+===============+============+==============+
| HelloWorldQTopicMDB   |             0 | True       |            0 |
+-----------------------+---------------+------------+--------------+
| HelloWorldQueueMDB    |             0 | True       |            0 |
+-----------------------+---------------+------------+--------------+
# MDB Delivery Active?
MDB[HelloWorldQueueMDB]: True
MDB[HelloWorldQTopicMDB]: True
```


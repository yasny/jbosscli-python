#!/usr/bin/env python
# -*- coding: utf-8 -*

import sys
import logging
import json
import requests
from tabulate import tabulate

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("jbosscli")

# disable requests logging
logging.getLogger("requests").setLevel(logging.CRITICAL)


class JBossHelper(object):
    """JBoss Application ServerのREST管理APIを簡単に利用するためのヘルパークラス。"""

    def __init__(self, url="http://localhost:9990/management", auth="admin:admin"):
        self.url = url
        self.credentials = auth.split(":")
        self._get_server_info()

    def _get_server_info(self):
        command = {"operation":"read-resource"}
        result = self._invoke(command)
        result = result['result']
        self.product_name = result['product-name']
        self.product_version = result['product-version']
        self.release_codename = result['release-codename']
        self.release_version = result['release-version']

    def _invoke(self, command):
        log.debug("Making request to %s with command %s"%(self.url, command))

        headers = {"Content-type": "application/json"}

        r = requests.post(
                self.url,
                data=json.dumps(command),
                headers=headers,
                auth=requests.auth.HTTPDigestAuth(self.credentials[0], self.credentials[1])
                )

        log.debug("Response code: %s"%r.status_code)

        if (r.status_code >= 400 and not r.text):
            raise JBossException("Got %s code from server."%(r.status_code))

        response = r.json()

        if 'outcome' not in response:
            raise JBossException("Unknown response: %s"%(r.text), response)

        if response['outcome'] != 'success':
            raise JBossException(response['failure-description'], response)

        return response

    def __str__(self):
        msg = "Connected to %s\nServer: %s (%s)"%(self.url, self.product_name, self.product_version)
        return msg

    def _get_mbean(self, mbean_type):
        command = {
                "operation":"read-resource",
                "include-runtime":"true",
                "address":[
                    {"core-service":"platform-mbean"},
                    {"type":mbean_type}
                    ]
                }
        return self._invoke(command)

    def get_used_heap(self):
        """使用しているヒープメモリと最大ヒープメモリサイズを取得する。

        Returns:
            使用ヒープ（バイト）と最大ヒープサイズ（バイト）
        """
        result = self._get_mbean('memory')
        heap_memory_usage = result['result']['heap-memory-usage']
        used_heap = heap_memory_usage['used']
        max_heap = heap_memory_usage['max']
        return (used_heap, max_heap)

    def get_thread_count(self):
        """稼働しているスレッド数と過去の最大スレッド数を取得する。

        Returns:
            スレッド数と過去の最大スレッド数
        """
        result = self._get_mbean('threading')
        thread_count = result['result']['thread-count']
        peak_thread_count = result['result']['peak-thread-count']
        return (thread_count, peak_thread_count)

    def get_jboss_status(self):
        """サーバ状況（running, stoppedなど）を取得する。"""
        command = {
                "operation":"read-attribute",
                "name":"server-state",
                "include-runtime":"true"
                }
        result = self._invoke(command)
        return result['result']

    def list_mdbs_by_deployment(self, deployment):
        """指定したdeploymentに対してMDB名をリスト化する。

        Args:
            deployment (str): デプロイメント名
        """
        command = {
                "operation":"read-children-names",
                "child-type":"message-driven-bean",
                "address":[
                    {"deployment":deployment},
                    {"subsystem":"ejb3"}
                    ]
                }
        result = self._invoke(command)
        return result['result']

    def get_mdbs_by_deployment(self, deployment):
        """指定したデプロイメントに対してMDBの統計情報などを取得し、リストとして返す。

        Args:
            deployment (str): デプロイメント名

        Returns:
            MessageDrivenBeanのリスト
        """
        command = {
                "operation":"read-children-resources",
                "child-type":"message-driven-bean",
                "include-runtime":"true",
                "address":[
                    {"deployment":deployment},
                    {"subsystem":"ejb3"}
                    ]
                }
        result = self._invoke(command)
        result = result['result']
        mdbs = []
        for bean in result:
            info = result[bean]
            mdb = MessageDrivenBean(bean, info['invocations'], info['delivery-active'], info['pool-current-size'])
            mdbs.append(mdb)
        return mdbs

    def get_mdb_status(self, deployment, mdb_list):
        """MDBのdelivery-active項目を表示する。

        Args:
            deployment (strg): デプロイメント名
            mdb_list (list): MDBの名前
        """
        for mdb in mdb_list:
            command = {
                    "operation":"read-resource",
                    "include-runtime":"true",
                    "address":[
                        {'deployment':deployment},
                        {"subsystem":"ejb3"},
                        {"message-driven-bean":mdb}
                        ]
                    }
            result = self._invoke(command)
            print("MDB[%s]: %s"%(mdb,result['result']['delivery-active']))


class MessageDrivenBean(object):
    def __init__(self, name, invocations, delivery, pool_count):
        self.name = name
        self.invocations = invocations
        self.delivery = delivery
        self.pool_count = pool_count

    def __str__(self):
        return "%s: Invocations = %s, Delivery = %s, Pool Count = %s"%(self.name, self.invocations, self.delivery, self.pool_count)


class JBossException(Exception):
    def __init__(self, msg, raw=None):
        self.msg = msg;
        self.raw = raw if raw else self.msg

    def __str__(self):
        return repr(self.msg)


def tabulate_mdb(mdbs, tablefmt='simple'):
    table = [[m.name, m.invocations, m.delivery, m.pool_count] for m in mdbs]
    print tabulate(table, headers=['Message Driven Bean', 'Invocations', 'Delivery', 'Pool Count'], tablefmt=tablefmt)


if __name__=="__main__":
    jboss = JBossHelper(auth="admin:Admin#70365")

    print(jboss)
    print("JBoss is %s."%jboss.get_jboss_status())

    print("HEAP: used:%s max:%s"%jboss.get_used_heap())
    print("THREAD: current:%s peak:%s"%jboss.get_thread_count())

    print("# get_mdbs_by_deployment()")
    mdbs = jboss.get_mdbs_by_deployment("wildfly-helloworld-mdb.war")
    tabulate_mdb(mdbs, tablefmt='grid')

    print("# MDB Delivery Active?")
    jboss.get_mdb_status('wildfly-helloworld-mdb.war',['HelloWorldQueueMDB','HelloWorldQTopicMDB'])



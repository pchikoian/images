import pickle
from multiprocessing import Process
from time import gmtime, strftime
import os
import threading
import traceback
import prometheus_client
from prometheus_client.core import CollectorRegistry
from prometheus_client import Gauge, Counter
from neo4j import GraphDatabase
import urllib3
from flask import Response, Flask

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')
SERVICE_URL = os.environ.get('NEO4J_SERVICE')
PREFIX = "neo4j_"
PROM_OUTPUT = []
BACKGROUND_CHECK = False
FLASK_FIRST_LAUNCH = True
NEO4J_DRIVER = None

# Query timeout in seconds
QUERY_TIMEOUT = int(os.environ.get('QUERY_TIMEOUT', '30'))

try:
    with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', encoding="utf-8") as f_file:
        POD_NAMESPACE = f_file.readline()
except Exception:
    POD_NAMESPACE = "neo4j"

app = Flask(import_name=__name__)

def background_collector():
    """Collecting Neo4j metrics in the background"""
    global FLASK_FIRST_LAUNCH

    if FLASK_FIRST_LAUNCH is True:
        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] Waiting for the web-server to start')
        FLASK_FIRST_LAUNCH = False
        threading.Timer(60, background_collector).start()
        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] The task of background collection of metrics has been successfully created')
    else:
        global BACKGROUND_CHECK
        if BACKGROUND_CHECK is True:
            print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [WARN] Another background collector is already running, skipping the current run')
        else:
            BACKGROUND_CHECK = True
            print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] Start background collecting Prometheus metrics')
            lst = []
            registry = CollectorRegistry()

            ### Database statuses ###
            neo4j_db_status = Gauge('neo4j_db_status', 'List of all databases with their status. 1 – online, 0 – all other statuses', ['name', 'address', 'currentStatus', 'namespace'], registry=registry)

            ### Transaction metrics ###
            neo4j_transaction_active = Gauge('neo4j_transaction_active', 'Number of currently active transactions', ['database', 'namespace'], registry=registry)
            neo4j_transaction_last_id = Gauge('neo4j_transaction_last_id', 'Last transaction ID seen', ['database', 'namespace'], registry=registry)

            ### Connection metrics ###
            neo4j_bolt_connections_active = Gauge('neo4j_bolt_connections_active', 'Number of active bolt connections', ['connector', 'namespace'], registry=registry)
            neo4j_bolt_connections_total = Gauge('neo4j_bolt_connections_total', 'Total number of bolt connections', ['namespace'], registry=registry)

            ### Page cache metrics (Enterprise/JMX only - may be empty) ###
            neo4j_page_cache_hits = Gauge('neo4j_page_cache_hits', 'Total page cache hits (Enterprise only)', ['database', 'namespace'], registry=registry)
            neo4j_page_cache_faults = Gauge('neo4j_page_cache_faults', 'Total page cache faults (Enterprise only)', ['database', 'namespace'], registry=registry)
            neo4j_page_cache_hit_ratio = Gauge('neo4j_page_cache_hit_ratio', 'Page cache hit ratio (Enterprise only)', ['database', 'namespace'], registry=registry)

            ### Store format info ###
            neo4j_store_format = Gauge('neo4j_store_format', 'Store format version (1=current, 0=other)', ['database', 'format', 'namespace'], registry=registry)

            print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [-] Getting the statuses of all tables in the cluster')
            try:
                global NEO4J_DRIVER
                NEO4J_DRIVER = GraphDatabase.driver("bolt://"+SERVICE_URL+":7687", auth=None)
                def neo_query_1():
                    global NEO4J_DRIVER
                    with NEO4J_DRIVER.session() as session:
                        result = session.run('SHOW DATABASES YIELD name, address, currentStatus')
                        neo4j_request_result = [record.data() for record in result]
                    with open('/tmp/result_db_status', 'wb') as f_file:
                        pickle.dump(neo4j_request_result, f_file)
                    print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [+] Database status query completed')
                p_1 = Process(target=neo_query_1, name='Process_request_1')
                p_1.start()
                p_1.join(timeout=QUERY_TIMEOUT)
                p_1.terminate()
                with open('/tmp/result_db_status', 'rb') as f_file:
                    neo4j_request_result = pickle.load(f_file)
            except Exception as e:
                neo4j_request_result = []
                print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] Error connecting to the database to get statuses: ' + str(e))
                print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] ' + traceback.format_exc())
            for db_list in neo4j_request_result:
                if db_list['currentStatus'] == 'online':
                    db_status = 1
                else:
                    db_status = 0
                neo4j_db_status.labels(name=db_list['name'], address=db_list['address'].split('.')[0], currentStatus=db_list['currentStatus'], namespace=POD_NAMESPACE).set(db_status)
            lst.append(prometheus_client.generate_latest(neo4j_db_status))

            ### Collect performance metrics from primary service ###
            print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [-] Collecting performance metrics from ' + SERVICE_URL)
            try:
                def neo_query_metrics():
                    global NEO4J_DRIVER
                    metrics_data = {
                        'stores': [],
                        'transactions': {},
                        'connections': {'total': 0, 'by_connector': {}},
                        'pool_info': {}
                    }
                    with NEO4J_DRIVER.session() as session:
                        # Get store sizes
                        result = session.run('SHOW DATABASES YIELD name, store')
                        store_data = [{'name': record['name'], 'store': record['store']} for record in result]
                        metrics_data['stores'] = store_data

                        # Get transaction count per database
                        result = session.run('SHOW TRANSACTIONS YIELD database RETURN database, count(*) as txCount')
                        tx_data = {record['database']: record['txCount'] for record in result}
                        metrics_data['transactions'] = tx_data

                        # Get connection statistics
                        result = session.run('CALL dbms.listConnections() YIELD connectionId, connector RETURN connector, count(connectionId) as count')
                        conn_data = {record['connector']: record['count'] for record in result}
                        metrics_data['connections']['by_connector'] = conn_data
                        metrics_data['connections']['total'] = sum(conn_data.values())

                        # Try to get JMX metrics for page cache and memory
                        try:
                            # Page cache metrics
                            result = session.run("CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Page cache') YIELD attributes RETURN attributes")
                            for record in result:
                                attrs = record['attributes']
                                metrics_data['page_cache'] = {
                                    'hits': attrs.get('Hits', {}).get('value', 0),
                                    'faults': attrs.get('Faults', {}).get('value', 0),
                                    'hit_ratio': attrs.get('HitRatio', {}).get('value', 0.0)
                                }
                        except Exception:
                            # JMX might not be available in community edition
                            pass

                        # Try to get transaction IDs
                        try:
                            for db_name in [s['name'] for s in store_data]:
                                result = session.run(f'SHOW TRANSACTIONS YIELD database, transactionId WHERE database = "{db_name}" RETURN max(transactionId) as maxId')
                                for record in result:
                                    if db_name not in metrics_data.get('tx_ids', {}):
                                        metrics_data['tx_ids'] = {}
                                    metrics_data['tx_ids'][db_name] = record['maxId'] if record['maxId'] else 0
                        except Exception:
                            pass

                    with open('/tmp/result_metrics', 'wb') as f_file:
                        pickle.dump(metrics_data, f_file)
                    print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [+] Performance metrics query completed')

                p_metrics = Process(target=neo_query_metrics, name='Process_metrics')
                p_metrics.start()
                p_metrics.join(timeout=QUERY_TIMEOUT)
                p_metrics.terminate()
                with open('/tmp/result_metrics', 'rb') as f_file:
                    metrics_data = pickle.load(f_file)

                # Process store format information
                for store_info in metrics_data.get('stores', []):
                    db_name = store_info['name']
                    store_format = str(store_info.get('store', 'unknown'))
                    # Set to 1 for the current format, creates a label for tracking format versions
                    neo4j_store_format.labels(database=db_name, format=store_format, namespace=POD_NAMESPACE).set(1)

                # Process transaction counts (active transactions)
                for db_name, tx_count in metrics_data.get('transactions', {}).items():
                    neo4j_transaction_active.labels(database=db_name, namespace=POD_NAMESPACE).set(tx_count)

                # Process transaction IDs
                for db_name, tx_id in metrics_data.get('tx_ids', {}).items():
                    neo4j_transaction_last_id.labels(database=db_name, namespace=POD_NAMESPACE).set(tx_id)

                # Process connection statistics by connector
                for connector, count in metrics_data.get('connections', {}).get('by_connector', {}).items():
                    neo4j_bolt_connections_active.labels(connector=connector, namespace=POD_NAMESPACE).set(count)

                # Total connections
                conn_total = metrics_data.get('connections', {}).get('total', 0)
                neo4j_bolt_connections_total.labels(namespace=POD_NAMESPACE).set(conn_total)

                # Process page cache metrics if available
                if 'page_cache' in metrics_data:
                    pc = metrics_data['page_cache']
                    neo4j_page_cache_hits.labels(database='system', namespace=POD_NAMESPACE).set(pc.get('hits', 0))
                    neo4j_page_cache_faults.labels(database='system', namespace=POD_NAMESPACE).set(pc.get('faults', 0))
                    neo4j_page_cache_hit_ratio.labels(database='system', namespace=POD_NAMESPACE).set(pc.get('hit_ratio', 0.0))

            except Exception as e:
                print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] Error collecting performance metrics: ' + str(e))
                print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] ' + traceback.format_exc())

            lst.append(prometheus_client.generate_latest(neo4j_transaction_active))
            lst.append(prometheus_client.generate_latest(neo4j_transaction_last_id))
            lst.append(prometheus_client.generate_latest(neo4j_bolt_connections_active))
            lst.append(prometheus_client.generate_latest(neo4j_bolt_connections_total))
            lst.append(prometheus_client.generate_latest(neo4j_page_cache_hits))
            lst.append(prometheus_client.generate_latest(neo4j_page_cache_faults))
            lst.append(prometheus_client.generate_latest(neo4j_page_cache_hit_ratio))
            lst.append(prometheus_client.generate_latest(neo4j_store_format))

            ### Long-running queries ###
            neo4j_db_slow_queries = Gauge('neo4j_db_slow_query', 'Queries that have been running for more than 10,000 milliseconds', ['database', 'transactionId', 'currentQueryId', 'status', 'activeLockCount', 'pageHits', 'cpuTimeMillis', 'waitTimeMillis', 'idleTimeSeconds', 'namespace', 'address'], registry=registry)
            neo4j_db_slow_queries_page_hits = Gauge('neo4j_db_slow_query_page_hits', 'Page hits amount of queries that have been running for more than 10,000 milliseconds', ['database', 'transactionId', 'currentQueryId', 'status', 'activeLockCount', 'cpuTimeMillis', 'waitTimeMillis', 'idleTimeSeconds', 'namespace', 'address'], registry=registry)

            # Collect from discovered nodes via environment variables
            nodes_found = False
            for key, value in os.environ.items():
                if ("NEO4J_CORE" in key or "NEO4J_REPLICA" in key) and "PORT_7687_TCP_ADDR" in key and not "ADMIN" in key:
                    nodes_found = True
                    db_adress = key.split('_')[0] + '-' + key.split('_')[1] + '-' + key.split('_')[2]
                    print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [-] Getting long queries from ' + db_adress.lower())
                    try:
                        NEO4J_DRIVER = GraphDatabase.driver("bolt://"+str(value)+":7687", auth=None)
                        def neo_query_2():
                            global NEO4J_DRIVER
                            with NEO4J_DRIVER.session() as session:
                                result = session.run('SHOW TRANSACTIONS YIELD database, transactionId, currentQueryId, status, activeLockCount, pageHits, elapsedTime, cpuTime, waitTime, idleTime WHERE elapsedTime.milliseconds > 10000 RETURN database, transactionId, currentQueryId, status, activeLockCount, pageHits, elapsedTime.milliseconds AS elapsedTimeMillis, cpuTime.milliseconds AS cpuTimeMillis, waitTime.milliseconds AS waitTimeMillis, idleTime.seconds AS idleTimeSeconds')
                                neo4j_request_result = [record.data() for record in result]
                            with open('/tmp/result_slow_queries', 'wb') as f_file:
                                pickle.dump(neo4j_request_result, f_file)
                            print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [+] Slow queries query completed')
                        p_2 = Process(target=neo_query_2, name='Process_request_2')
                        p_2.start()
                        p_2.join(timeout=QUERY_TIMEOUT)
                        p_2.terminate()
                        with open('/tmp/result_slow_queries', 'rb') as f_file:
                            neo4j_request_result = pickle.load(f_file)
                    except Exception as e:
                        neo4j_request_result = []
                        print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] Error connecting to the ' + db_adress.lower() + ' to get long queries: ' + str(e))
                        print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] ' + traceback.format_exc())
                    for db_list in neo4j_request_result:
                        neo4j_db_slow_queries.labels(database=db_list['database'], transactionId=db_list['transactionId'], currentQueryId=db_list['currentQueryId'], status=db_list['status'], activeLockCount=db_list['activeLockCount'], pageHits=db_list['pageHits'], cpuTimeMillis=db_list['cpuTimeMillis'], waitTimeMillis=db_list['waitTimeMillis'], idleTimeSeconds=db_list['idleTimeSeconds'], namespace=POD_NAMESPACE, address=db_adress.lower()).set(db_list['elapsedTimeMillis'])
                        neo4j_db_slow_queries_page_hits.labels(database=db_list['database'], transactionId=db_list['transactionId'], currentQueryId=db_list['currentQueryId'], status=db_list['status'], activeLockCount=db_list['activeLockCount'], cpuTimeMillis=db_list['cpuTimeMillis'], waitTimeMillis=db_list['waitTimeMillis'], idleTimeSeconds=db_list['idleTimeSeconds'], namespace=POD_NAMESPACE, address=db_adress.lower()).set(db_list['pageHits'])

            # If no cluster nodes found, collect from primary service
            if not nodes_found:
                print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [-] No cluster nodes found, collecting long queries from primary service: ' + SERVICE_URL)
                try:
                    NEO4J_DRIVER = GraphDatabase.driver("bolt://"+SERVICE_URL+":7687", auth=None)
                    def neo_query_2_primary():
                        global NEO4J_DRIVER
                        with NEO4J_DRIVER.session() as session:
                            result = session.run('SHOW TRANSACTIONS YIELD database, transactionId, currentQueryId, status, activeLockCount, pageHits, elapsedTime, cpuTime, waitTime, idleTime WHERE elapsedTime.milliseconds > 10000 RETURN database, transactionId, currentQueryId, status, activeLockCount, pageHits, elapsedTime.milliseconds AS elapsedTimeMillis, cpuTime.milliseconds AS cpuTimeMillis, waitTime.milliseconds AS waitTimeMillis, idleTime.seconds AS idleTimeSeconds')
                            neo4j_request_result = [record.data() for record in result]
                        with open('/tmp/result_slow_queries_primary', 'wb') as f_file:
                            pickle.dump(neo4j_request_result, f_file)
                        print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] [+] Slow queries query completed')
                    p_2_primary = Process(target=neo_query_2_primary, name='Process_request_2_primary')
                    p_2_primary.start()
                    p_2_primary.join(timeout=QUERY_TIMEOUT)
                    p_2_primary.terminate()
                    with open('/tmp/result_slow_queries_primary', 'rb') as f_file:
                        neo4j_request_result = pickle.load(f_file)
                    for db_list in neo4j_request_result:
                        neo4j_db_slow_queries.labels(database=db_list['database'], transactionId=db_list['transactionId'], currentQueryId=db_list['currentQueryId'], status=db_list['status'], activeLockCount=db_list['activeLockCount'], pageHits=db_list['pageHits'], cpuTimeMillis=db_list['cpuTimeMillis'], waitTimeMillis=db_list['waitTimeMillis'], idleTimeSeconds=db_list['idleTimeSeconds'], namespace=POD_NAMESPACE, address=SERVICE_URL).set(db_list['elapsedTimeMillis'])
                        neo4j_db_slow_queries_page_hits.labels(database=db_list['database'], transactionId=db_list['transactionId'], currentQueryId=db_list['currentQueryId'], status=db_list['status'], activeLockCount=db_list['activeLockCount'], cpuTimeMillis=db_list['cpuTimeMillis'], waitTimeMillis=db_list['waitTimeMillis'], idleTimeSeconds=db_list['idleTimeSeconds'], namespace=POD_NAMESPACE, address=SERVICE_URL).set(db_list['pageHits'])
                except Exception as e:
                    print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] Error getting long queries from primary service: ' + str(e))
                    print (strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [ERROR] ' + traceback.format_exc())

            lst.append(prometheus_client.generate_latest(neo4j_db_slow_queries))
            lst.append(prometheus_client.generate_latest(neo4j_db_slow_queries_page_hits))

            ### Final set of metrics ###
            global PROM_OUTPUT
            PROM_OUTPUT = lst
            print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ' [INFO] Prometheus metrics have been successfully collected in the background')

            BACKGROUND_CHECK = False

        threading.Timer(240, background_collector).start()

background_collector()

@app.route("/")
def hello():
    """Displaying the root page"""
    return "This is a Prometheus Exporter. Go to the /metrics page to get metrics"

@app.route('/metrics', methods=['GET'])
def metrics():
    """Displaying the Prometheus Metrics page"""
    return Response(PROM_OUTPUT,mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    app.run(debug=True)

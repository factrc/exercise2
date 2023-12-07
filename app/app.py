import Queue
import threading
import json
import time
import logging
import sys
import faker
import random
import requests
import os


from clickhouse_driver import Client
from rediscluster import RedisCluster

logger = logging.getLogger(__name__)

config_filename = 'config.json'
config = None

class ClickHouse_Connector:
    def __init__(self,config):
        self.nodes = config.get('clickhouse',None)
        self.database = config.get('database',None)
        self.table = config.get('table',None)
        self.conn = None
        if (self.nodes and self.database and self.table ):
            self.conn = Client(host=self.nodes[0],alt_hosts=','.join(self.nodes[1:]))
    def get_DatabaseName(self):
        return self.database
    def get_TableName(self):
        return self.table
    def get_TableFullName(self):
        return self.database+'.'+self.table
    def connect(self):
        return self.conn
    def isValid(self):
        return True if self.conn else False

class Redis_Connector:
    def __init__(self,config):
        self.queue = config.get('queue',None)
        self.nodes = config.get('redis',None)
        self.conn = None
        if self.queue and self.nodes:
            self.conn = RedisCluster(startup_nodes=self.nodes, decode_responses=True,skip_full_coverage_check=True)
    def connect(self):
        return self.conn
    def isValid(self):
        return True if self.conn else False
    def get_QueueName(self):
        return self.queue


def ProcessingPastbin(filequeue, msg ):
    api_key = config.get('pastbin_key')
    if os.getenv('PASTBIN_KEY'):
        api_key = os.getenv('PASTBIN_KEY')
    api_endpoint = config.get('pastbin_endpoint')
    data = {'api_dev_key':api_key,'api_option':'paste','api_paste_code':msg,'api_paste_format':'json'}
    r = requests.post(url = api_endpoint, data = data)
    if ( r.ok ):
        filequeue.put(r.text)
    else:
        logger.info("error paste to %s: %s",api_endpoint,r.content)
    return 

def ProcessingFileQueue(filequeue):
    filename = config.get('result_file','result.log')
    while True:
        v = filequeue.get()
        with open(filename,'a+t') as f:
            f.write(v+'\n')
            logger.info('write to file %s',v)
        filequeue.task_done()
    return 

def ProcessingQueue( name, myqueue, filequeue ):
    c = ClickHouse_Connector(config)
    if c.isValid() == False:
        return 
    while True:
        v = myqueue.get()
        logger.info('%s got value: %s %s %d',name,v['ip'],v['mac'],v['id'])
        ret = []
        columns = []
        try:
            ret,columns = c.connect().execute("select * from %s where ip='%s' and mac='%s' FORMAT JSONEachRow;"%(c.get_TableFullName(),v['ip'],v['mac']), with_column_types=True)
            if len(ret):
                msg = json.dumps(dict(zip([col[0] for col in columns],[ x for x in ret[0] ])))
                logger.info('%s match: %s',name,msg)
                ProcessingPastbin(filequeue,msg)
        except:
            logger.info('wrong request')
        myqueue.task_done()

def start_thread_pool(count):
    thread_pool = [ None for _ in range(count+1)]
    work_queue = Queue.Queue()
    file_queue = Queue.Queue()
    for i in range(count):
        name_process = 'ProcessingQueue-%d'%i
        thread_pool[i] = threading.Thread(target=ProcessingQueue,name=name_process,args=(name_process,work_queue,file_queue,))
        thread_pool[i].daemon = True
        thread_pool[i].start()
    thread_pool[-1] = threading.Thread(target=ProcessingFileQueue,name='File logger',args=(file_queue,))
    thread_pool[-1].daemon = True
    thread_pool[-1].start()
    return thread_pool,work_queue

def CoreDispatcher(count):
    c = Redis_Connector(config)
    if c.isValid() == False:
        return 3
    pool,work_queue = start_thread_pool(config.get('parallel_count',1))
    while True:
        for _ in range(c.connect().llen(c.get_QueueName())):
            v = json.loads(c.connect().lpop(c.get_QueueName()))
            if v.get('id',None) == None or v.get('ip',None) == None or v.get('mac',None) == None:
                logger.info('From Redis get invalid task:')
                continue
            logger.info('From Redis get task: id: %d ip:%s mac:%s',v['id'],v['ip'],v['mac'])
            work_queue.put(v)
        time.sleep(config.get('dispatch_timeout',1))
    return 0

def loading_users(dbusers):
    c = ClickHouse_Connector(config)
    if c.isValid() == False:
        return False
    logger.info('Creating database')    
    c.connect().execute("CREATE DATABASE IF NOT EXISTS %s ON CLUSTER 'company_test' COMMENT 'test database';"%c.get_DatabaseName())
    logger.info('Creating table')    
    c.connect().execute("CREATE TABLE IF NOT EXISTS %s ON CLUSTER 'company_test' ( `username` String,`ip` String,`mac` String ) \
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{cluster}/{shard}/%s', '{replica}') PARTITION BY username PRIMARY KEY (ip, mac);" % (c.get_TableFullName(),c.get_TableFullName() ))
    logger.info('Loading user to database...')
    for i,user in enumerate(dbusers):
        c.connect().execute('INSERT INTO %s (*) VALUES (\'%s\',\'%s\',\'%s\');' % (c.get_TableFullName(),user['username'],user['ip'],user['mac']))
        if ( i and i%100 == 0 ):
            logger.info('Loading... %d records',i)
    logger.info('Loading completed.')
    return True

def loading_tasks(dbtasks):
    rc = Redis_Connector(config)
    if rc.isValid() == False:
        return False
    logger.info('Create tasks...')
    for i,v in enumerate(dbtasks):
        rc.connect().rpush(rc.get_QueueName(),json.dumps(v))
        if ( i and i%100 == 0 ):
            logger.info('Loading... %d tasks',i)
    logger.info('Task created.')
    return True

def make_faker_data():
    users = config.get('users',0)
    tasks = config.get('tasks',0)
    valid_tasks = config.get('valid_tasks',0)
    if ( users == 0 ):
        return False
    users = max(users,valid_tasks)
    tasks = max(tasks,valid_tasks)
    fake = faker.Faker()
    dbusers = []
    for i in range(users):
        user = { 'username': str(fake.name()), 'ip': str(fake.ipv4()), 'mac': str(fake.mac_address())}
        dbusers.append(user)
    dbtasks = []
    for id in range(tasks-valid_tasks):
        task = { 'id': id, 'ip': str(fake.ipv4()), 'mac': str(fake.mac_address())}
        dbtasks.append(task)
    for id in range(tasks,tasks+valid_tasks):
        r = random.randint(0,len(dbusers)-1)
        task = { 'id': id, 'ip': dbusers[r]['ip'], 'mac': dbusers[r]['mac'] }
        dbtasks.append(task)
    return loading_users(dbusers) and loading_tasks(dbtasks)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S',level=logging.INFO)
    with open(config_filename,'r') as f:
        config = json.load(f)
    if(not config ):
        logger.info('config not found')
        sys.exit(1)
    if ( not make_faker_data() ):
        logger.info('make_faker_data == False')
        sys.exit(2)
    sys.exit(CoreDispatcher(10))


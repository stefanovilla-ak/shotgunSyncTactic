import os
import sys
sys.path.append(os.environ['AK_ROOT'])

os.environ['TACTIC_SERVER']='tactictest'

from Animoka.Tactic import Server as TacticServer
import ak_environment


class tactic_file(object):
    '''
    equivalent of 'published' table in tactic
    '''

    tactic_server = None
    file_data = None
    file_name = None
    checkin_dir = None
    source_path = None
    relative_dir = None
    def __init__(self,tactic_server, file_data):
        self.tactic_server = tactic_server
        self.file_data = file_data
        self.file_name = self.file_data['file_name']
        self.checkin_dir = self.file_data['checkin_dir']
        self.source_path = self.file_data['source_path']
        self.relative_dir = self.file_data['relative_dir']
        return

class tactic_snapshot(object):
    '''
    equivalent of 'version' table in tactic
    '''

    tactic_server = None
    snapshot = None
    tactic_files = None
    def __init__(self, tactic_server, snapshot):
        self.tactic_server = tactic_server
        self.snapshot = snapshot
        self.scan_snapshot()
        return
    def scan_snapshot(self):
        '''
        scan 'table' file for 'snapshot_code'
        :return:
        '''
        s_file_eval = '@SOBJECT(sthpw/file["snapshot_code", "{}"])'.format( self.snapshot['code'])
        s_file_objects = self.tactic_server.eval(s_file_eval)
        for s_file_object in s_file_objects:
            if self.tactic_files is None: self.tactic_files=[]
            self.tactic_files.append(tactic_file(self.tactic_server ,s_file_object))
        return

class tactic_task(object):
    tactic_server = None
    task = None
    tactic_snapshots = None
    def __init__(self, tactic_server, task):
        self.tactic_server = tactic_server
        self.task = task
        self.scan_task()
        return
    def scan_task(self):
        project_code = self.task['search_type'].split('?')[1]
        project_code = project_code.split('=')[1]
        s_snapshot_eval = '@SOBJECT(sthpw/snapshot["search_code", "{}"]["search_type", "{}"]["project_code", "{}"])'.format(self.task['search_code'], self.task['search_type'], project_code)
        s_snapshot_objects = self.tactic_server.eval(s_snapshot_eval)
        if s_snapshot_objects:
            for s_snapshot_object in sorted(s_snapshot_objects, key=lambda d: d['version']) :
                if self.tactic_snapshots is None: self.tactic_snapshots = []
                self.tactic_snapshots.append(tactic_snapshot(self.tactic_server ,s_snapshot_object))
        '''
        SELECT * FROM "public"."snapshot" WHERE "search_code"='RIG00002' and "search_type"='delu/rig?project=delu' ORDER BY "version";'''
        return

class tactic_element(object):
    tactic_server = None
    # in case a %table%_code is found, such as 'rig_code', %table% is sought for and:
    element_raw = None              # this is the raw rappresentation
    element_full_raw = None
    element_class = None
    # tasks
    tactic_tasks = None
    def __init__(self, tactic_server, element):
        self.tactic_server = tactic_server
        self.element_raw = element
        self.element_full_raw = element
        self.element_class = element
        self.scan_element()
        return
    def scan_element(self):
        for key in self.element_raw:
            '''
            {'relative_dir': 'test_delu_4/asset', 'rig_code': 'RIG00002', 'code': 'ASSET00002', '_is_collection': False, 'description': None, 'asset_category_code': 'pr', 'tags': None, 'timestamp': '2022-01-25 09:38:14.839782', 's_status': None, 'pipeline_code': 'test_delu_4/asset', '__search_key__': 'test_delu_4/asset?project=test_delu_4&code=ASSET00002', 'keywords': None, 'rig': None, 'login': None, 'data': None, 'id': 2, '__search_type__': 'test_delu_4/asset?project=test_delu_4', 'name': 'pr_generico'}
            '''
            if key.endswith('_code'):
                entitry = key[:-len('_code')]
                project = self.element_raw['__search_type__'].split('?')[1].replace('project=','')
                s_entitry_eval = '@SOBJECT({}/{}["code", "{}"])'.format(project, entitry, self.element_raw[key])
                try:
                    s_entitry_objects = self.tactic_server.eval(s_entitry_eval)
                    self.element_full_raw[key] = s_entitry_objects
                    self.element_class[key] = None # class definition for a specific table is yet to be done..
                except:
                    if key not in ['pipeline_code']:
                        print('couldnt evaluate {}'.format(key))
                        print(self.element_raw)
        self.scan_for_tasks()


        return
    def scan_for_tasks(self):
        # SELECT * FROM "public"."task" where "search_code"='SHOT00003' AND "project_code"='test_delu_4';
        project = self.element_raw['__search_type__'].split('?')[1].replace('project=', '')
        s_tasks_eval = '@SOBJECT(sthpw/task["search_code", "{}"]["project_code", "{}"])'.format(self.element_raw['code'], project)
        s_tasks_objects = self.tactic_server.eval(s_tasks_eval)
        for s_tasks_object in s_tasks_objects:
            if self.tactic_tasks is None: self.tactic_tasks = []
            self.tactic_tasks.append(tactic_task(self.tactic_server ,s_tasks_object))
        return

class tactic_sobject(object):
    '''
    A SObject is the equivalent of an 'entity' in Shotgrid.
    'Asset','Shot','Sequence' and 'Episode' do exists in both project setup
    Each SObject/Entity has its own set of tasks, which depends on the type of SObject/Entity
    '''
    sobject = None
    tactic_server = None
    tactic_object = None
    def __init__(self, tactic_server, sobject):
        self.tactic_server = tactic_server
        self.sobject = sobject
        self.scan_sobject()
        return
    def scan_sobject(self):
        '''
        from a SOobject must query the 'table' to get a list of Objects to get to their tasks..
        :return:
        '''
        s_object_eval = '@SOBJECT({})'.format(self.sobject['code'])
        s_objects = self.tactic_server.eval(s_object_eval)
        for s_object in s_objects:
            if self.tactic_object is None: self.tactic_object = []
            self.tactic_object.append(tactic_element(self.tactic_server, s_object))
        return

class tactic_project(object):
    tactic_server = None
    project_code = None
    tactic_project = None              # tactic_project structure
    tactic_sobjects = None
    legit_stypes = None
    def __init__(self, project_code):
        self.user = ak_environment.TACTIC_USER
        self.tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER, project=project_code, user=self.user, password=ak_environment.TACTIC_PASSWORD)
        self.project_code = project_code
        self.init_project()
        if self.tactic_project:
            self.scan_tactic_project()
        return

    def init_project(self, project_code=None):
        if project_code is not None:
            self.project_code = project_code

        search_eval = "@SOBJECT(sthpw/project['code', '{}'])".format(self.project_code)
        try:
            self.tactic_project = self.tactic_server.eval(search_eval)[0]
        except BaseException as err:
            print('Error occured in init_project: {}'.format(err))
            self.tactic_project = None
        else:
            print ('self.tactic_project = {}'.format(self.tactic_project))
        return self.tactic_project

    def scan_tactic_project(self):
        # get valid stype, that is those stype with tasks
        task_per_project_eval = '@SOBJECT(config/process["pipeline_code", "NEQ", "{}"])'.format('task')
        tasks_per_project = self.tactic_server.eval(task_per_project_eval)
        for t in tasks_per_project:
            legit_stype = t['pipeline_code'].split('/')[-1]
            if self.legit_stypes is None: self.legit_stypes = {}
            if legit_stype not in self.legit_stypes:
                self.legit_stypes[legit_stype]=[]
            if t['process'] not in self.legit_stypes[legit_stype]:
                self.legit_stypes[legit_stype].append(t['process'])
        # get all stypes.
        s_object_eval = '@SOBJECT(sthpw/search_object["code", "EQ", "^{}"])'.format(self.tactic_project['code'])
        for search_object in self.tactic_server.eval(s_object_eval):
            if search_object['table_name'] not in self.legit_stypes.keys(): continue
            if self.tactic_sobjects is None: self.tactic_sobjects = []
            self.tactic_sobjects.append(tactic_sobject(self.tactic_server, search_object))
        return

    def get_stype(self, stype=None):
        if not self.tactic_sobjects: return []
        return list(self.legit_stypes.keys())
    def get_sobject(self, stype, code=None):
        return
    def get_task(self, stype, code, tcode=None):
        return
    def get_files(self, stype, code, tcode, version=None):
        return


def get_project(code):
    tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                        project=code,
                                        user=ak_environment.TACTIC_USER,
                                        password=ak_environment.TACTIC_PASSWORD)

    search_eval = "@SOBJECT(sthpw/project['code', '{}'])".format(code)
    tactic_project = tactic_server.eval(search_eval)[0]
    return  tactic_project

def get_tasks_from_sobject(project, stype, name=None):
    tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                        project=project['code'],
                                        user=ak_environment.TACTIC_USER,
                                        password=ak_environment.TACTIC_PASSWORD)

    sobject_eval = '@SOBJECT({}/{}["name", "{}"])'.format(project['code'], stype, name)
    sobject = tactic_server.eval(sobject_eval)
    if not sobject: return None
    sobject = sobject[0]

    s_tasks_eval = '@SOBJECT(sthpw/task["search_code", "{}"]["project_code", "{}"])'.format(sobject['code'], project['code'])
    s_tasks_objects = tactic_server.eval(s_tasks_eval)

    return s_tasks_objects

def get_snapshots_(search_code, project_code):
    tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                        project=project_code,
                                        user=ak_environment.TACTIC_USER,
                                        password=ak_environment.TACTIC_PASSWORD)

    #SELECT * FROM "public"."snapshot" WHERE "search_code"='ASSET00702' AND "project_code"='mfe' AND "is_latest" is TRUE;
    s_snapshot_eval = '@SOBJECT(sthpw/snapshot["search_code", "{}"]["project_code", "{}"]["is_latest", "True"])'.format(search_code, project_code)
    s_snapshot_objects = tactic_server.eval(s_snapshot_eval)
    return s_snapshot_objects

def get_snapshots(task):
    tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                        project=task['project_code'],
                                        user=ak_environment.TACTIC_USER,
                                        password=ak_environment.TACTIC_PASSWORD)

    #SELECT * FROM "public"."snapshot" WHERE "search_code"='ASSET00702' AND "project_code"='mfe' AND "is_latest" is TRUE and 'process'=.. and "contetx"=..;
    s_snapshot_eval = '@SOBJECT(sthpw/snapshot["search_code", "{}"]' \
                      '["project_code", "{}"]' \
                      '["is_latest", "True"]["context", "{}"],["process", "{}"])'.format(task['search_code'], task['project_code'], task['process'], task['process'])
    s_snapshot_objects = tactic_server.eval(s_snapshot_eval)
    return s_snapshot_objects

def get_file_from_snapshot(snapshot):
    tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                        project=snapshot['project_code'],
                                        user=ak_environment.TACTIC_USER,
                                        password=ak_environment.TACTIC_PASSWORD)

    s_file_eval = '@SOBJECT(sthpw/file["snapshot_code", "{}"]["project_code", "{}"])'.format(snapshot['code'], snapshot['project_code'])
    s_file_objects = tactic_server.eval(s_file_eval)
    return s_file_objects

def get_last_version(tactic_tasks):
    '''
    :param tactic_tasks:    all tasks relative to an asset
    :return:
    '''
    version_task = {}
    # for each task (design, model, etc=
    for tactic_task in tactic_tasks:
        # get its last snapshot filtered by process
        #NOTE: filtering by process will exclude all context like "process/pb*"
        snapshots = get_snapshots(tactic_task)
        # no need to filter out complex context (process/pb*) as it has been already filtered out in get_snapshots()
        #snapshots_no_pb = [x for x in snapshots if x['context']==x['process']]
        version_task[tactic_task['process']]={'task': tactic_task, 'file':[]}
        # for each snapshot (there should one actually)
        for snapshot_no_pb in snapshots:
            # get its file info
            file = get_file_from_snapshot(snapshot_no_pb)
            if not file: continue
            file = file[0]
            version_task[tactic_task['process']]['file'].append(file)

    return version_task

def get_sobjects(project_code):
    tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                        project=project_code,
                                        user=ak_environment.TACTIC_USER,
                                        password=ak_environment.TACTIC_PASSWORD)

    #SELECT * FROM "public"."search_object" WHERE "namespace"='mfe' AND "title" IS NOT NULL;
    s_snapshot_eval = '@SOBJECT(sthpw/search_object["namespace", "{}"]["title", "NEQ", "NULL"]])'.format(project_code)
    s_snapshot_objects = tactic_server.eval(s_snapshot_eval)
    return s_snapshot_objects

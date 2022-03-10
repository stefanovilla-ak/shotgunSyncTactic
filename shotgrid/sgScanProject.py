# coding=utf-8
import shotgun_api3
import json
from shotgrid import sg


class sg_file(object):
    '''
    equivalent of 'file' table in tactic
    '''
    file_data = None
    file_name = None


class sg_version(object):
    '''
    equivalent of 'snapshot' table in tactic
    '''
    version_raw = None
    s_publish = None

    def __init__(self, version):
        self.version_raw = version
        self.scan_version()
        return

    def scan_version(self):
        return


class sg_task(object):
    task = None
    s_versions = None

    def __init__(self, task):
        self.task = sg.sg.find_one('Task', [['id', 'is', task['id']]], sg.get_fields('Task'))
        self.scan_task()
        return

    def scan_task(self):
        versions = sg.sg.find('Version', [['sg_task', 'is', self.task]], sg.get_fields('Version'))
        if not versions: return
        for version in versions:
            if self.s_versions is None: self.s_versions = []
            self.s_versions.append(sg_version(version))
        return


class sg_element(object):
    # in case a %table%_code is found, such as 'rig_code', %table% is sought for and:
    element_raw = None  # this is the raw rappresentation
    element_full_raw = None
    element_class = None
    # tasks
    s_tasks = None

    def __init__(self, element):
        self.element_raw = element
        self.element_full_raw = element
        self.element_class = element
        self.scan_element()
        return

    def scan_element(self):
        if 'tasks' not in self.element_raw: return
        for s_task in self.element_raw['tasks']:
            if self.s_tasks is None: self.s_tasks = []
            self.s_tasks.append(sg_task(s_task))
        return


class sg_entity(object):
    '''
    A SObject is the equivalent of an 'entity' in Shotgrid.
    'Asset','Shot','Sequence' and 'Episode' do exists in both project setup
    Each SObject/Entity has its own set of tasks, which depends on the type of SObject/Entity
    '''
    entity_code = None
    elements_raw = None
    elements = None

    def __init__(self, entity_code, elements):
        self.entity_code = entity_code
        self.elements_raw = elements
        if not self.elements_raw: return
        self.scan_entity()
        return

    def scan_entity(self):
        for element in self.elements_raw:
            if self.elements is None: self.elements = []
            self.elements.append(sg_element(element))


class sg_project(object):
    project_code = None
    sg_project = None
    sg_entities = None
    sg_task_templates = None
    sg_steps = None
    def __init__(self, project_code):
        self.project_code = project_code
        self.sg_project = None
        self.init_project()
        if self.sg_project:
            self.scan_sg_project()
        else:
            print('cannot find project "{}"'.format(self.project_code))
        return
    def init_project(self):
        fields = sg.get_fields('Project')
        self.sg_project = sg.sg.find_one("Project", [['name', 'is', self.project_code]], fields)
        return self.sg_project
    def scan_sg_project(self):
        for stype in ['Asset', 'Shot', 'Sequence', 'Episode', 'Rig']:
            s_entity_code_d = sg.get_entity_from_name(stype)
            s_entity_name = (list(s_entity_code_d.keys())[0])
            s_entity_code = s_entity_code_d[s_entity_name]
            print('------------ {} -------------- {}'.format(s_entity_code, s_entity_name))
            s_elements = sg.sg.find(s_entity_code, [['project', 'is', {'type': 'Project', 'id': self.sg_project['id']}]], sg.get_fields(s_entity_code))
            if self.sg_entities is None: self.sg_entities = []
            self.sg_entities.append(sg_entity(s_entity_code_d, s_elements))
        #
        self.sg_task_templates = sg.sg.find('TaskTemplate', [], sg.get_fields('TaskTemplate'))
        self.sg_steps = sg.sg.find('Step', [], sg.get_fields('Step'))
        print('done')
        return
    def get_entities(self):
        return ([list(x.entity_code.keys())[0] for x in self.sg_entities])


def create_project(sg_project):
    print('going to create project {}'.format(sg_project.project_code))
    return
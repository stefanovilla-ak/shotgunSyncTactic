# coding=utf-8
import shotgun_api3
import json
from functools import lru_cache

sg = shotgun_api3.Shotgun("https://stefanovilla.shotgrid.autodesk.com",
                          script_name='sg_test',
                          api_key='lmugajlw-yvdsUlwonaznyq0d')

global_entities = sg.schema_entity_read()


@lru_cache(maxsize=None)
def get_entity_from_name(name, entity=False):
    print(name)
    try:
        if entity:
            return [x for x in global_entities if global_entities[x]['name']['value'] == name][0]
        else:
            return {name:[x for x in global_entities if global_entities[x]['name']['value'] == name][0]}
    except:
        return None


def get_fields(entity, exclude_datetime=True, datetime_only=False):
    '''
    Returns all columns of an entity.
    :param entity:
    :param exclude_datetime:    if True excludes all column of type 'datetime'
                                        (mostly because cannot be serialized into a json for printing purposes)
    :param datetime_only:       if True returns only those columns of type 'datetime'
    :return:
    '''
    fields = []
    date_time_fields = []
    data = sg.schema_field_read(entity)
    if datetime_only: exclude_datetime = True
    for field in data:
        if data[field]['data_type']['value'] == 'date_time':
            date_time_fields.append(field)
        else:
            fields.append(field)
    if datetime_only:
        return date_time_fields
    elif exclude_datetime:
        return fields
    return fields + date_time_fields


def get_project(project_code):
    fields = get_fields('Project')
    sg_project = sg.find_one("Project", [['name', 'is', project_code]], fields)
    return sg_project

def create_sg_project(project_code, project_title=None):
    if project_title is None: project_title=project_code
    print('GOING TO CREATE PROJECT {}'.format(project_code))
    project_data = {
        "name": project_code,
        "sg_type": "Other",  # Must match - this is based on a vanilla Shotgun site
        "sg_description": project_title,
        "layout_project": {"id": 63, "type": "Project"},  # code 63 is the Template Project in a default site
    }
    projectCreated = sg.create("Project", project_data)
    return projectCreated

def get_task_ny_id(id_):
    fields = get_fields('Task')
    sg_task = sg.find_one("Task", [['id', 'is', id_]], fields)
    return sg_task

def get_taskTemplate(task_template_name):
    fields = get_fields('TaskTemplate')
    sg_task_template = sg.find_one("TaskTemplate", [['code', 'is', task_template_name]], fields)
    return sg_task_template

def get_taskTemplateProcesses(task_template_name, sort_by_process=False):
    taskTemplate = get_taskTemplate(task_template_name)
    # get all tasks for taskTemplate
    fields = get_fields('Task')
    sg_task_for_template = sg.find("Task", [['task_template', 'is', taskTemplate]], fields)
    if sort_by_process:
        return {x["content"]:x for x in sg_task_for_template}
    return sg_task_for_template

def missing_processes(tactic_processes, task_template):
    missing_processes=[]
    if type(tactic_processes) not in [list, tuple]: tactic_processes=[tactic_processes]
    for tactic_process in tactic_processes:
        taskTemplate = get_taskTemplateProcesses(task_template)
        if tactic_process not in [x["content"] for x in taskTemplate]:
            missing_processes.append(tactic_process)
    return list(missing_processes)

def get_generic_element(sg_entity, sobject_name,  sg_project):
    fields = get_fields(sg_entity)
    sg_elem = sg.find_one(sg_entity, [['code', 'is', sobject_name], ['project', 'is', sg_project]], fields)
    return sg_elem

def get_tasks_from(sg_entity):
    return sg_entity['tasks']

def create_entity(sg_entity, name, sg_tasks_for_template, sg_project):
    print('must create a new element:\n\tproject: {}\n\tentity: {}\n\tname: {}\n\ttasks: {}'.format(sg_project['name'],
                                                                                                    sg_entity,
                                                                                                    name,
                                                                                                    sg_tasks_for_template.keys()))

    # first create tasks
    keys_from_template = ["pinned","est_in_mins","step","content",
	"duration","milestone","notes","implicit","color","splits","task_assignees",
	"cached_display_name","sg_description","filmstrip_image",
	"tags",
	"sg_status_list"]
    newly_created_tasks = []
    siblings = []
    task_template = None
    for process in list(sg_tasks_for_template.keys()):
        # just set it once for later...
        if task_template is None: task_template=sg_tasks_for_template[process]["task_template"]
        data = { "entity": None,         #to be filled after entity creation
                "upstream_tasks": [],   #to be filled after tasks creation
                "downstream_tasks": [], #to be filled after tasks creation
                "template_task":{"name": sg_tasks_for_template[process]["content"],
                                 "id": sg_tasks_for_template[process]["id"],
                                 "type": sg_tasks_for_template[process]["type"]}, #sg_tasks_for_template[process],
                ##READONLY"sibling_tasks":[],     #to be filled after tasks creation
                "project":{
                    "id": sg_project["id"],
                    "name": sg_project["name"],
                    "type": "Project"}
                }
        for key_from_template in keys_from_template:
            data[key_from_template]=sg_tasks_for_template[process][key_from_template]

        new_task = sg.create('Task', data)
        #siblings.append({"name": new_task["name"], "id": new_task["id"], "type": new_task["type"]})
        newly_created_tasks.append(new_task)
    # # update siblings ## READONLY
    # for task in newly_created_tasks:
    #     data = {"sibling_tasks":siblings}
    #     sg.update("Task", task[id], data)
    #todo: create upstream/downstream

    # create Entity
    tasks = [{"name": x["content"], "id": x["id"], "type": x["type"]} for x in newly_created_tasks]
    data = {"tasks":tasks,
            "sg_versions":[],
            "code":name,
            "cached_display_name":name,
            "description":"automatically created",
            "tags":[],
            "task_template":task_template,
            "project":sg_project,
            }
    if sg_entity=='Asset':
        data["episodes"] = [],
        data["sequences"]= []
        data["shots"]= []
        data["assets"]= []
    elif sg_entity=='Shot':
        data["shots"]= []
        data["assets"]= []
    new_asset = sg.create(sg_entity, data)

    #update tasks
    for task in newly_created_tasks:
        data = {"entity":new_asset}
        sg.update("Task", task['id'], data)

    return new_asset, newly_created_tasks


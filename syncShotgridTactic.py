# coding=utf-8
import os
import sys
os.environ['AK_ROOT'] = r'V:\home\svilla\dev\ak_utils\Python'

import argparse

import shotgrid.sgScanProject as scanProject
import tactic.tactic as tactic
import syncProjects
from shotgrid import sg
from tactic import tactic
import lookupTable as lt
from shotgrid import sgVersion

def old_syncShotgridTactic(args):
    print(args.dry_run)
    print(args.project)

    # read and init tactic structure
    tactic_project = tactic.tactic_project(args.project)
    if tactic_project.tactic_project is None:
        print('Must provide an existing project. {} does not exist in Tactic'.format(args.project) )
        return
    print('tactic_project = {}'.format(tactic_project))

    # read and init shotgrid project
    #sg_project = scanProject.sg_project(args.project)
    #print('sg_project = {}'.format(sg_project))


    # sync shotgun over tactic
    #syncProjects.sync_projects(tactic_project, sg_project, args.stype, args.task)
    return


def get_task_from_taskTemplate(real_sg_entity):
    # get task_template from stype
    sg_task_template = sg.get_taskTemplate(real_sg_entity)
    if not sg_task_template: return None

    # get all tasks for taskTemplate sorted by 'content' (design, model, etc)
    return sg.get_taskTemplateProcesses(sg_task_template['code'], sort_by_process=True)


def syncShotgridTacticSobject(tactic_data):
    #unpack data
    tactic_project = tactic_data['tactic_project']
    project_code = tactic_data['project_code']
    stype_code = tactic_data['stype_code']
    sobject_code = tactic_data['sobject_code']
    task_code = tactic_data['task_code']

    # 0.1 get tasks from tactic sobject
    tactic_tasks = tactic.get_tasks_from_sobject(project=tactic_project, stype=stype_code, name=sobject_code)
    # get last version for each task
    versions = tactic.get_last_version(tactic_tasks)

    # defines the list of process to sync
    tactic_process_request = list(versions.keys())
    if task_code:
        if task_code in versions.keys():
            tactic_process_request = [task_code]

    # verify tasks to sync do exist in shotgun TaskTemplates
        # get proper taskTemplate as define in lookupTable
    real_sg_entity = lt.sg_asset_template_lt[lt.tactic_sg_asset_lt[stype_code]]
    missing_process = sg.missing_processes(tactic_process_request, real_sg_entity)
    if missing_process:
        print('The following processes {} are missing within taskTemplate {} '.format(','.join(list(missing_process)), real_sg_entity))
        exit(-1)


    # 1. check project existence in shotgun
    sg_project = sg.get_project(project_code)

    #   1.1 create if missing
    if not sg_project:
        sg.create_sg_project(project_code)
    sg_project = sg.get_project(project_code)

    #  2.
    # get shotgun entity raw name (CustomEntity02)
    sg_entity = sg.get_entity_from_name(lt.tactic_sg_asset_lt[stype_code], entity=True)

    # 3.
    # check for the existence of required sobject
    sg_elem = sg.get_generic_element(sg_entity, sobject_code, sg_project)

    # get task from taskTemplate sorted by context
    sg_task_for_template_by_context = get_task_from_taskTemplate(real_sg_entity)

    # create entity if does not exists with appropriate set of tasks
    if not sg_elem:
        sg_elem, sg_tasks = sg.create_entity(sg_entity=sg_entity,
                                             name=sobject_code,
                                             sg_tasks_for_template=sg_task_for_template_by_context,
                                             sg_project=sg_project)
    else:
        sg_tasks = sg.get_tasks_from(sg_elem)

    # version only those tasks that match requirements
    for task in sg_tasks:
        if task['name'] in tactic_process_request:
            files = versions[task['name']]['file']
            if files:
                relative_dir = files[0]['relative_dir']
                folder_to_scan = os.path.abspath(os.path.join(r'V:\prod', relative_dir))
                if os.path.exists(folder_to_scan):
                    print('goingto version {}'.format(folder_to_scan))
                    #sgVersion.version(project=sg_project, asset=sg_elem, task=task, folder_to_scan=folder_to_scan, images_only = False, movies_only = True, geometry_only = False)
                else:
                    print('Requested folder {} does not exist'.format(folder_to_scan))
    return


def syncShotgridTactic(args):
    '''
    1. check project existence in shotgun
    . create if missing
    check project's tasks existence:
        .create taskTemplates if missing

2. for all sobjects:
    check sobject existence in shotgun
        . create sobject if missing with proper task taskTemplate

    3. for all sobject's tasks:
        check task existence:
            .create task is missing

    :param args:
    :return:
    '''
    tactic_data = {
    'project_code': args.project,
    'stype_code': args.stype,
    'sobject_code': args.name,
    'task_code': None,
    }
    try:
        tactic_data['task_code'] = args.task
    except:
        pass
    print("syncronizing {}.{}.{}.{} over Shotgrid".format(tactic_data['project_code'],
                                                          tactic_data['stype_code'],
                                                          tactic_data['sobject_code'] if tactic_data['sobject_code'] else '*',
                                                          tactic_data['task_code'] if tactic_data['task_code'] else '*'))

    # 0. check project in tactic
    tactic_data['tactic_project'] = tactic.get_project(tactic_data['project_code'])
    if not tactic_data['tactic_project']:
        print('project {} does not exist in Tactic'.format(tactic_data['project_code']))
        return False

    # 1. sync requested sobjects
    # if sobject is not provided look for all sobject in project
    if not tactic_data['sobject_code']:
        sobjects = tactic.get_sobjects(tactic_data['project_code'])
        for sobject in sobjects:
            tactic_data['sobject_code'] = sobject
            syncShotgridTacticSobject(tactic_data)
    else:
        syncShotgridTacticSobject(tactic_data)

    return


def get_parser():
    description = "Syncronize Tactic project in Shotgrid." \
                  "\n\nIt'll create project if doesn't exist and it'll update it if it does" \
                  "\n\nStype (Asset, Shot, Sequence,Episode or Rig) must be provided." \
                  "\n\nName, if not provided sync is performed on all sobject of stype." \
                  "\n\nIf task/process (model, rigging, layout, etc) is provided " \
                  "sync will be performed on such task only, otherwise on all sobject's tasks"
    parser = argparse.ArgumentParser(description=description, add_help=False)
    parser.add_argument('-d', '--dry-run', dest='dry_run', help='If set prints out changes only', action="store_true")
    parser.add_argument('-p', '--project', dest='project', help='Tactic Project name to be sync in Shotgrid', required=True)
    parser.add_argument('-s', '--stype', dest='stype', help='Tactic Stype to sync', required=True)
    parser.add_argument('-n', '--name', dest='name', help='Sobject\'s name to sync', required=False)
    parser.add_argument('-t', '--task', dest='task', help='Tactic Stype\'s task to sync', required=False)
    return parser

if __name__ == '__main__':
    args = None
    try:
        args = get_parser().parse_args()
    except BaseException as err:
        print('------------------------------------')
        get_parser().print_help()
        exit(-1)
    else:
        syncShotgridTactic(args)




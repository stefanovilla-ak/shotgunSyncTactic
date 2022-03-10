# coding=utf-8
import os
import sys
import json
import argparse

os.environ['AK_ROOT'] = r'V:\home\svilla\dev\ak_utils\Python'
sys.path.append(os.environ['AK_ROOT'])

from Animoka.Tactic import Server as TacticServer
import ak_environment

import shotgrid.sgScanProject as scanProject
import tactic.tactic as tactic

import shotgun_api3
from shotgrid import sg
from shotgrid import sgVersion
'''
# inputs: project, [[sobject], [task]]
if no sobject and not task is given all tasks (last version) for all sobjects are synced within shotgun

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


'''
tactic_sg_asset_lt = {'asset':'Asset', 'shot':'Shot','sequence':'Sequence','rig':'Rig', 'episode':'Episode'}
sg_asset_template_lt = {'Asset':'AssetTemplate','Shot':'ShotTemplate','Rig':'RiggingTemplate','Episode':'EpisodeTemplate' }

project_code = 'mfe'

# tactic_stype = 'asset'
# tactic_sobject_name = 'pr_amphoraSingleHandle_3'
# tactic_process = 'model'

tactic_stype = 'shot'
tactic_sobject_name = 'ep101_sh0230'
tactic_process = 'compositing'

tactic_stype = 'rig'
tactic_sobject_name = 'rig_generico'
tactic_process = 'rigging'

tactic_server = TacticServer.Server(server=ak_environment.TACTIC_SERVER,
                                    project=project_code,
                                    user=ak_environment.TACTIC_USER,
                                    password=ak_environment.TACTIC_PASSWORD)


'''
# get tactic project
search_eval = "@SOBJECT(sthpw/project['code', '{}'])".format(project_code)
tactic_project = tactic_server.eval(search_eval)[0]
print(tactic_project)

# 1. check project existence in shotgun
sg_project = sg.get_project(project_code)
#   1.1 create if missing
if not sg_project:
    sg.create_sg_project(project_code)
sg_project = sg.get_project(project_code)
'''

'''
# get tactic project
tactic_project = tactic.get_project(project_code)
# get tasks from tactic sobject
tactic_tasks = tactic.get_tasks_from_sobject(name=tactic_sobject_name, stype=tactic_stype, project=tactic_project)
# get last version for each task
versions = tactic.get_last_version(tactic_tasks)
# defines the list of process to sync
tactic_process_request = versions.keys()
if tactic_process:
    if tactic_process in versions.keys():
        tactic_process_request = [tactic_process]

# verify they do exist in shotgun TaskTemplates
missing_process = sg.missing_processes(tactic_process_request, sg_asset_template_lt[tactic_sg_asset_lt[tactic_stype]])
if missing_process:
    print('The following processes {} are missing within taskTemplate {} '.format(','.join(missing_process),
                                                                                  sg_asset_template_lt[tactic_sg_asset_lt[tactic_stype]]))
    exit(-1)

for tactic_process in tactic_process_request:
    pass
'''



sg_project = sg.get_project(project_code)

# get shotgun entity name (Rig)
sg_entity_name = tactic_sg_asset_lt[tactic_stype]

# get shotgun entity raw name (CustomEntity02)
sg_entity = sg.get_entity_from_name(sg_entity_name, entity=True)

# get task_template from stype
sg_task_template = sg.get_taskTemplate(sg_asset_template_lt[tactic_sg_asset_lt[tactic_stype]])

# get all tasks for taskTemplate sorted by 'content' (design, model, etc)
sg_task_for_template_by_context = sg.get_taskTemplateProcesses(sg_task_template['code'], sort_by_process=True)



# check for the existence of such sobject
sg_elem = sg.get_generic_element(sg_entity, tactic_sobject_name, sg_project)

if not sg_elem:
    sg_elem, sg_tasks = sg.create_entity(sg_entity=sg_entity,
                                         name=tactic_sobject_name,
                                         sg_tasks_for_template=sg_task_for_template_by_context,
                                         sg_project=sg_project)
else:
    sg_tasks = sg.get_tasks_from(sg_elem)

# for task in sg_tasks:
#     sgVersion.version(project=sg_project, asset=sg_elem, task=task, folder_to_scan, images_only = False, movies_only = True, geometry_only = False)


print('')











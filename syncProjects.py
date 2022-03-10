# coding=utf-8
import os
import sys
from operator import ixor

from shotgrid import sgEditProject



def check_for_entities(tactic_project, sg_project):
    '''
    verifies that names and number of tactic.stype matches name and number of shotgun.stype
    Any mismatch must be solved manually
    :param tactic_project:
    :param sg_project:
    :return:
    '''
    stypes = [x.lower() for x in sorted(tactic_project.get_stype())]
    entities = [x.lower() for x in sorted(sg_project.get_entities())]
    entities_missing =  list(set(stypes) - set(entities))
    if entities_missing:
        print('must create a new entity/ies in shotgun whose name/s must be "{}"'.format(','.join(entities_missing)))
        return False
    return True

def sync_projects(tactic_project, sg_project, stype, tactic_task):

    if not sg_project.sg_project:
        sgEditProject.create_sg_project(tactic_project)
        print('A new shotgrid projects named "{}" has been created.. please run this again..'.format(tactic_project.project_code))
        return False
    #check for stype/entity match
    if not check_for_entities(tactic_project, sg_project):
        return False
    #todo: for each stype/entity check for task match
    #       verify the existance of shotgrid template (template_name must be defined on a config file)
    #           the correctness of each task template to have the same tasks as tactic is manual

    #todo: for each sobject create a shotgrid entity
    #   todo: for each sobject's task create the equivalent entity's task
    #       todo: for each task create a shotgun version with its content..


    return True
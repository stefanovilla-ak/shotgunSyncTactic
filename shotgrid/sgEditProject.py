# coding=utf-8
import shotgun_api3
import json
from shotgrid import sg


def create_sg_project(tactic_project):
    print('GOING TO CREATE PROJECT {}'.format(tactic_project.project_code))
    project_data = {
        "name": tactic_project.project_code,
        "sg_type": "Other",  # Must match - this is based on a vanilla Shotgun site
        "sg_description": tactic_project.tactic_project['title'],
        "layout_project": {"id": 63, "type": "Project"},  # code 63 is the Template Project in a default site
    }
    projectCreated = sg.sg.create("Project", project_data)
    return projectCreated
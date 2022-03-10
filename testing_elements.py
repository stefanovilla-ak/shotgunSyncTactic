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


sg_project_mfe = sg.get_project('mfe')
aa = sg.get_generic_element('Asset', 'pr_amphoraSingleHandle_1', sg_project_mfe)
print(aa)
taa = sg.get_task_ny_id(5983)

sg_project_testnt = sg.get_project('test_no_templates')
bb = sg.get_generic_element('Asset', 'pr_amphoraSingleHandle_2', sg_project_testnt)
print(bb)
tbb = sg.get_task_ny_id(5977)
print(tbb)


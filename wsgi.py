import sys
import os

project_home = '/home/majordarren/propaganda-compass'
if project_home not in sys.path:
    sys.path.append(project_home)

from app import create_app

application = create_app()
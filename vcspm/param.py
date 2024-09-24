import os
from pathlib import Path


class Param:
    vcspm_dir = ".vcspm"
    cache_dir_name = ".vcspm"
    repository_url = ""
    install_dir = "vcspm/packages"
    patches_dir = "vcspm/patches"
    vcspm_file = "vcspm.json"

    root_dir = os.getcwd()
    home_dir = Path.home()

    install_path = ""

    cache_dir = os.path.join(home_dir, cache_dir_name)

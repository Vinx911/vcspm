import os

from vcspm import utils
from vcspm.logger import logging
from vcspm.param import Param

DEFAULT_PNUM = 3


class Package:
    def __init__(self, name, info):
        self.clean = False
        self.name = name
        self.info = info
        self.version = info.get('version', '')
        self.include = info.get('include', None)
        self.exclude = info.get('exclude', None)
        self.post = info.get('post_process', None)

    def download(self):
        pass

    def post_process(self):
        if self.post is None:
            return 0

        if 'type' not in self.post:
            logging.error("无效的格式 {}, 'post_process'必须包含 'type' ".format(self.name))
            return -1
        if 'file' not in self.post:
            logging.error("无效的格式 {}, 'post_process'必须包含 'file' ".format(self.name))
            return -1

        post_type = self.post['type']
        post_file = self.post['file']

        package_dir = os.path.join(Param.install_path, self.name)
        patches_path = os.path.join(Param.patches_dir, self.name)

        if post_type == "patch":
            patch_path = os.path.join(patches_path, post_file)
            utils.apply_patch_file(patch_path, package_dir, self.post.get('pnum', DEFAULT_PNUM))
        elif post_type == "script":
            script_path = os.path.join(patches_path, post_file)
            utils.run_python_script(script_path, self.name + " \"" + package_dir + "\"")
        else:
            logging.error("{} 未知的 post_process 类型 {}".format(self.name, post_type))
            return -1

    def package_path(self):
        return os.path.join(Param.install_path, self.name)

    def cache_path(self):
        return os.path.join(Param.cache_dir, self.name[0].lower(), self.name, self.version)

    def __eq__(self, other):
        if other is None:
            return False

        return self.info == other.info

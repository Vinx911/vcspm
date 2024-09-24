import os
import shutil

from vcspm import utils
from vcspm.package import Package


class LocalPackage(Package):

    def __init__(self, name, info):
        super().__init__(name, info)
        self.url = info.get('url', None)
        self.path = info.get('path', None)
        self.path = self.path or self.url

    def download(self):
        package_path = self.package_path()

        if self.clean:
            shutil.rmtree(package_path)
            os.makedirs(package_path)

        if self.path is None:
            err_msg = "本地包 {} 的 path 为空".format(self.name)
            raise RuntimeError(err_msg)

        utils.copy_tree(self.path, package_path, include=self.include, exclude=self.exclude)

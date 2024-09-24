import os
import shutil

from vcspm import utils, extractor
from vcspm.logger import logging
from vcspm.package import Package

SHELL_SVN = "svn"


class SvnPackage(Package):

    def __init__(self, name, info):
        super().__init__(name, info)
        self.url = info.get('url', None)
        self.svn_url = info.get('svn', None)

        self.svn_url = self.svn_url or self.url

        if self.svn_url is None:
            raise

    def _clone_svn_repository(self, local_path):
        """
        从svn仓库下载包
        """
        target_path = utils.escapify_path(os.path.join(local_path, self.name))
        target_exists = os.path.exists(target_path)
        logging.info("克隆 {} 到 {}".format(self.svn_url, target_path))

        if target_exists:
            logging.debug("克隆前删除 " + target_path)
            shutil.rmtree(target_path)
        utils.die_if_non_zero(utils.exec_shell("{} checkout {} {}".format(SHELL_SVN, self.svn_url, target_path)))

        return target_path

    def download(self):
        package_path = self.package_path()
        cache_path = self.cache_path()

        shutil.rmtree(package_path, onerror=utils.delete)
        os.makedirs(package_path)

        # 克隆后压缩缓存
        archive_name = self.name + ".tar.gz"
        archive_sha1 = archive_name + ".sha256"
        archive_path = os.path.join(cache_path, archive_name)
        archive_sha1_path = os.path.join(cache_path, archive_sha1)

        # 如果已经存在则检查SHA1是否匹配
        if (not self.clean) and os.path.exists(archive_path) and os.path.exists(archive_sha1_path):
            sha1_hash = open(archive_sha1_path).read()
            hash_file = utils.compute_file_sha256(archive_path)
            if hash_file == sha1_hash:
                logging.info("包 {} 已经下载，将使用缓存的包。".format(self.name))
                extractor.extract_file_and_filter(archive_path, package_path, include=self.include,
                                                  exclude=self.exclude)
                return

        repo_path = self._clone_svn_repository(cache_path)
        utils.copy_tree(repo_path, package_path, include=self.include, exclude=self.exclude)
        utils.create_archive_from_directory(repo_path, archive_path, True)
        hash_file = utils.compute_file_sha256(archive_path)
        with open(archive_sha1_path, 'w') as f:
            f.write(hash_file)
        shutil.rmtree(repo_path, onerror=utils.delete)

import os
import shutil

from vcspm import utils, extractor
from vcspm.logger import logging
from vcspm.package import Package

SHELL_GIT = "git"


class GitPackage(Package):

    def __init__(self, name, info):
        super().__init__(name, info)
        self.url = info.get('url', None)
        self.git_url = info.get('git', None)
        self.revision = info.get('revision', None)

        self.git_url = self.git_url or self.url

        if self.git_url is None:
            raise

    def _clone_git_repository(self, local_path):
        """
        从git仓库下载包
        """
        target_path = utils.escapify_path(os.path.join(local_path, self.name))
        target_exists = os.path.exists(target_path)
        logging.info("克隆 {} 到 {}".format(self.git_url, target_path))

        repo_exists = os.path.exists(os.path.join(target_path, ".git"))

        if not repo_exists:
            if target_exists:
                logging.debug("克隆前删除 " + target_path)
                shutil.rmtree(target_path)
            utils.die_if_non_zero(
                utils.exec_shell("{} clone --recursive {} {}".format(SHELL_GIT, self.git_url, target_path))
            )
        else:
            logging.info("仓库 {} 已经存在，将进行拉取".format(target_path))
            utils.die_if_non_zero(
                utils.exec_shell("{} -C {} fetch --recurse-submodules".format(SHELL_GIT, target_path))
            )

        if self.revision is None:
            self.revision = "HEAD"

        utils.die_if_non_zero(
            utils.exec_shell("{} -C {} reset --hard {}".format(SHELL_GIT, target_path, self.revision))
        )
        utils.die_if_non_zero(
            utils.exec_shell("{} -C {} clean -fxd".format(SHELL_GIT, target_path))
        )

        return target_path

    def download(self):
        package_path = self.package_path()
        cache_path = self.cache_path()

        shutil.rmtree(package_path, onerror=utils.delete)
        os.makedirs(package_path)

        # 克隆后压缩缓存
        archive_name = self.name + ".tar.gz"
        if self.revision is not None:
            archive_name = self.name + "_" + self.revision + ".tar.gz"
        archive_sha1 = archive_name + ".sha256"
        archive_path = os.path.join(cache_path, archive_name)
        archive_sha1_path = os.path.join(cache_path, archive_sha1)

        # 如果已经存在则检查SHA1是否匹配
        if (not self.clean) and os.path.exists(archive_path) and os.path.exists(archive_sha1_path):
            sha1_hash = open(archive_sha1_path).read()
            hash_file = utils.compute_file_sha256(archive_path)
            if hash_file == sha1_hash:
                logging.info("包 {} 已经下载，将使用缓存文件".format(self.name))
                extractor.extract_file_and_filter(archive_path, package_path, include=self.include,
                                                  exclude=self.exclude)
                return

        repo_path = self._clone_git_repository(cache_path)
        utils.copy_tree(repo_path, package_path, include=self.include, exclude=self.exclude)
        utils.create_archive_from_directory(repo_path, archive_path, self.revision is None)
        hash_file = utils.compute_file_sha256(archive_path)

        with open(archive_sha1_path, 'w') as f:
            f.write(hash_file)

        shutil.rmtree(repo_path, onerror=utils.delete)

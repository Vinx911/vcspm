import os
import shutil

from vcspm import param, downloader
from vcspm import extractor
from vcspm.logger import logging
from vcspm.package import Package


class ArchivePackage(Package):

    def __init__(self, name, info):
        super().__init__(name, info)
        self.url = info.get('url', None)
        self.hash_type = info.get('hash_type', None)
        self.file_hash = info.get('file_hash', None)
        self.rm_top_dir = info.get('rm_top_dir', False)

    def download(self):
        package_path = self.package_path()
        cache_path = self.cache_path()

        if self.clean:
            shutil.rmtree(package_path)
            os.makedirs(package_path)

        cache_file = None
        if type(self.url) is list:
            for url in self.url:
                try:
                    url = url.replace("${version}", self.version)
                    cache_file = downloader.download_file(url, cache_path, self.hash_type, self.file_hash,
                                                          force=self.clean)
                    break
                except Exception as e:
                    logging.info(str(e))
                    continue
        else:
            url = self.url.replace("${version}", self.version)
            cache_file = downloader.download_file(url, cache_path, self.hash_type, self.file_hash, force=self.clean)

        if cache_file is None:
            if type(self.url) is list:
                url = [url.replace("${version}", self.version) for url in self.url]
                err_msg = "下载文件失败: {}".format(url)
            else:
                url = self.url.replace("${version}", self.version)
                err_msg = "下载文件失败: {}".format(url)
            raise RuntimeError(err_msg)

        extractor.extract_file_and_filter(cache_file, package_path, self.rm_top_dir, include=self.include,
                                          exclude=self.exclude)

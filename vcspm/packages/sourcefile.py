import os
import shutil

from vcspm import downloader
from vcspm.logger import logging
from vcspm.package import Package


class SourceFilePackage(Package):

    def __init__(self, name, info):
        super().__init__(name, info)
        self.url = info.get('url', None)
        self.hash_type = info.get('hash_type', None)
        self.file_hash = info.get('file_hash', None)

    def download(self):
        package_path = self.package_path()
        cache_path = self.cache_path()

        if self.clean:
            shutil.rmtree(package_path)
            os.makedirs(package_path)

        try:
            cache_file = None
            if type(self.url) is list:
                for url in self.url:
                    try:
                        cache_file = downloader.download_file(url, cache_path, self.hash_type, self.file_hash,
                                                              force=self.clean)
                        break
                    except Exception as e:
                        logging.info(str(e))
                        continue
            else:
                cache_file = downloader.download_file(self.url, cache_path, self.hash_type, self.file_hash,
                                                      force=self.clean)

            filename = os.path.basename(self.url)
            shutil.copyfile(cache_file, os.path.join(package_path, filename))
        except:
            shutil.rmtree(package_path)
            raise

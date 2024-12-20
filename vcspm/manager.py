import json
import os
import shutil

from logger import logging
from packages.archive import ArchivePackage
from packages.git import GitPackage
from packages.hg import HgPackage
from packages.local import LocalPackage
from packages.sourcefile import SourceFilePackage
from packages.svn import SvnPackage
from vcspm import downloader, extractor
from vcspm.param import Param


class Manager:

    def __init__(self):
        self.install_dir = ""
        self.repository_url = ""
        self.packages = {}

    def package_names(self):
        return self.packages.keys()

    def remove(self, pkg_name):
        for _, pkg in self.packages.items():
            if pkg.name == pkg_name:
                self.packages.pop(pkg)
                break

    def toJson(self, filename):
        data = {
            "install_dir": self.install_dir,
            "repository_url": self.repository_url
        }

        pkgs = {}
        for _, pkg in self.packages.items():
            pkgs[pkg.name] = pkg.info

        data["packages"] = pkgs

        with open(filename, 'w') as outfile:
            json.dump(data, outfile)

    @staticmethod
    def fromJson(path):
        try:
            jsonData = open(path).read()
        except:
            logging.error("无法读取Json文件: " + path)
            return None

        try:
            data = json.loads(jsonData)
            vcspm = Manager()
            vcspm.install_dir = data.get("install_dir")
            vcspm.repository_url = data.get("repository_url")

            pkg_list = data.get("packages") or {}
            pkg_names = pkg_list.keys()
            for pkg_name in pkg_names:
                info = pkg_list.get(pkg_name)
                vcspm.packages[pkg_name] = Manager._create_package(pkg_name, info)

        except json.JSONDecodeError as e:
            logging.error("无法解析Json文档: {}\n    {} (line {}:{})\n".format(path, e.msg, e.lineno, e.colno))
            return None
        except:
            logging.error("无法解析Json文档: " + path)
            return None

        return vcspm

    # 从仓库获取包信息
    @staticmethod
    def _get_package_info_from_repository(pkg_name, pkg_version):
        """
        从远程仓库中获取包信息
        """
        package_url = "{}/{}/{}/{}".format(Param.repository_url, pkg_name[0].lower(), pkg_name, pkg_version)

        info_url = "{}/{}".format(package_url, "vcspm.json")
        patch_url = "{}/{}".format(package_url, "patch.zip")

        cache_path = os.path.join(Param.cache_dir, pkg_name[0].lower(), pkg_name, pkg_version)
        try:
            info_file = downloader.download_file(info_url, cache_path, force=False)
            json_data = open(info_file).read()
            data = json.loads(json_data)
            pkg = Manager._create_package(pkg_name, data)

            if pkg is None:
                return None
        except:
            shutil.rmtree(cache_path)
            return None

        try:
            patch_file = downloader.download_file(patch_url, cache_path, force=False)
            patch_dir = os.path.join(Param.patches_dir, pkg_name)
            extractor.extract_file(patch_file, patch_dir)
        except:
            pass

        return pkg

    @staticmethod
    def _create_package(pkg_name, info):
        if type(info) is str:
            return Manager._get_package_info_from_repository(pkg_name, info)

        if 'type' not in info:
            raise RuntimeError("未指定包 {} 的类型".format(pkg_name))

        package_type = info['type']
        if package_type == "local":
            return LocalPackage(pkg_name, info)
        elif package_type == "sourcefile":
            return SourceFilePackage(pkg_name, info)
        elif package_type == "archive":
            return ArchivePackage(pkg_name, info)
        elif package_type == "git":
            return GitPackage(pkg_name, info)
        elif package_type == "hg":
            return HgPackage(pkg_name, info)
        elif package_type == "svn":
            return SvnPackage(pkg_name, info)
        else:
            raise ValueError("不支持的包类型： " + package_type)

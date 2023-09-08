#!/usr/bin/env python
#
#    Vinx C/C++ Source Package Manager
#    Copyright (C) 2023 Vinx911 <Buddyhe911@163.com>
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import traceback
from pathlib import Path
from urllib.parse import urlparse

import paramiko
import requests
import scp
from vcspm import decompress, version

VCSPM_DIR = ".vcspm"
CACHE_DIR_NAME = ".vcspm"
INSTALL_DIR = "vcspm/packages"
PATCHES_DIR = "vcspm/patches"
VCSPM_FILE = "vcspm.json"

ROOT_DIR = os.getcwd()
HOME_DIR = Path.home()

CACHE_DIR = os.path.join(HOME_DIR, CACHE_DIR_NAME)

DEFAULT_PNUM = 3

# 调试开关
debug_output = True

SHELL_GIT = "git"
SHELL_HG = "hg"
SHELL_SVN = "svn"
SHELL_PATCH = "patch"
SHELL_PYTHON = "python"

if not sys.version_info[0] >= 3:
    raise ValueError("本工具需要Python 3.0或更高版本")


class HelpFormatter(argparse.HelpFormatter):
    def _format_action_invocation(self, action: argparse.Action) -> str:
        formatted = super()._format_action_invocation(action)
        if action.option_strings and action.nargs != 0:
            formatted = formatted.replace(
                f" {self._format_args(action, self._get_default_metavar_for_optional(action))}",
                "",
                len(action.option_strings) - 1,
            )

        return formatted


def log_info(string):
    print("---[INFO] " + string)


def log_error(string):
    print("---[ERROR] " + string, file=sys.stderr)


def log_debug(string):
    if debug_output:
        print("***[DEBUG] " + string)


def delete(func, path, execinfo):
    os.chmod(path, stat.S_IWUSR)
    func(path)


# 执行命令
def exec_shell(command, print_command=False, quiet=False):
    print_command = print_command or debug_output

    out = None
    err = None

    if quiet:
        out = subprocess.DEVNULL
        err = subprocess.STDOUT

    if print_command:
        if debug_output:
            log_debug("> " + command)
        else:
            log_info("> " + command)

    return subprocess.call(command, shell=True, stdout=out, stderr=err)


def die_if_non_zero(res):
    if res != 0:
        raise ValueError("命令返回非零状态: " + str(res))


# 转义路径
def escapify_path(path):
    if path.find(" ") == -1:
        return path
    if platform.system() == "Windows":
        return "\"" + path + "\""
    return path.replace("\\ ", " ")


# 复制文件
def copy_tree(src, dst, include=None, exclude=None):
    # 包含的文件
    include_files = set()
    if include is not None and len(include) > 0:
        for pat in include:
            for file in Path(src).rglob(pat):
                include_files.add(file)
    else:
        for file in Path(src).rglob("*"):
            include_files.add(file)

    # 排除的文件
    exclude_files = set()
    if exclude is not None:
        for pat in exclude:
            for file in Path(src).rglob(pat):
                exclude_files.add(file)

    # 移除排除的文件
    for file in include_files.copy():
        if file in exclude_files:
            include_files.remove(file)

    # 复制文件
    for file in include_files:
        src_path = os.path.split(file)[0]
        src_relpath = os.path.relpath(src_path, src)

        dst_path = os.path.join(dst, src_relpath)
        if not os.path.isdir(dst_path):
            os.makedirs(dst_path)

        file_relpath = os.path.relpath(file, src)
        dst_file = os.path.join(dst, file_relpath)
        if not os.path.isdir(file):
            shutil.copy2(file, dst_file)


def readJsonData(filename):
    try:
        json_data = open(filename).read()
    except:
        log_info("ERROR: 无法读取Json文件: " + filename)
        return None

    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        log_info("ERROR: 无法解析Json文档: {}\n    {} (line {}:{})\n".format(filename, e.msg, e.lineno, e.colno))
        return None
    except:
        log_info("ERROR: 无法解析Json文档: " + filename)
        return None

    return data


def writeJsonData(data, filename):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)


# 列出全部包
def list_packages(package_list):
    for pkg_name in package_list.keys():
        package = package_list.get(pkg_name)
        if type(package) is str:
            pkg_version = package
            print("{}/{}".format(pkg_name, pkg_version))
        else:
            pkg_version = package.get('version', None)
            if pkg_version is None:
                print("{}".format(pkg_name))
            else:
                print("{}/{}".format(pkg_name, pkg_version))


# 从仓库获取包信息
def get_package_info_from_repository(service_url, pkg_name, pkg_version, patch_dir):
    """
    从远程仓库中获取包信息
    """
    package_url = "{}/{}/{}/{}".format(service_url, pkg_name[0].lower(), pkg_name, pkg_version)

    info_url = "{}/{}".format(package_url, "vcspm.json")
    patch_url = "{}/{}".format(package_url, "patch.zip")

    cache_path = os.path.join(CACHE_DIR, pkg_name[0].lower(), pkg_name, pkg_version)
    try:
        info_file = download_file(info_url, cache_path, force=False)
        # 读取依赖包文件
        package = readJsonData(info_file)
        if package is None:
            return None
    except:
        shutil.rmtree(cache_path)
        return None

    try:
        patch_file = download_file(patch_url, cache_path, force=False)
        extract_file(patch_file, patch_dir)
    except:
        pass

    return package


# #下载进度条
def download_progress(cur_size, total_size):
    try:
        percent = int((cur_size / total_size) * 100)
        percent = percent if percent <= 100 else 100
        percent = percent if percent >= 0 else 0
    except:
        percent = 100

    print("[", end="")
    for i in range(int(percent / 2)):
        print("*", end="")
    for i in range(int(percent / 2), 50):
        print(".", end="")
    print("] " + str(percent) + "% --- ", end="")
    print("%.2f" % (cur_size / 1024), "KB", end="\r")


# 计算sha256值
def compute_file_sha256(filename):
    block_size = 65536
    hasher = hashlib.sha256()
    with open(filename, 'rb') as f:
        buf = f.read(block_size)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(block_size)
    return hasher.hexdigest()


# 计算sha1值
def compute_file_sha1(filename):
    block_size = 65536
    hasher = hashlib.sha1()
    with open(filename, 'rb') as f:
        buf = f.read(block_size)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(block_size)
    return hasher.hexdigest()


def check_hash(file_path, hash_type="SHA256", file_hash=None):
    """
    检查文件hash
    """
    if os.path.exists(file_path) and file_hash is not None and file_hash != "":
        if hash_type == "SHA256":
            hash_file = compute_file_sha256(file_path)
            if hash_file != file_hash:
                return False
        elif hash_type == "SHA1":
            hash_file = compute_file_sha1(file_path)
            if hash_file != file_hash:
                return False
    return True


def extract_file(filepath, target_dir):
    """
    解压文件
    :param filepath: 压缩包
    :param target_dir: 解压路径
    :return:
    """
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    log_info("解压缩 " + filepath)
    filename = os.path.basename(filepath)

    if filename.endswith(".zip"):
        decompress.decompress_zip(filepath, target_dir)
    elif filename.endswith(".7z"):
        decompress.decompress_tar_xz(filepath, target_dir)
    elif filename.endswith(".tar.gz") or filename.endswith(".tar.bz2"):
        decompress.decompress_tar(filepath, target_dir)
    elif filename.endswith(".tgz"):
        decompress.decompress_tar(filepath, target_dir)
    elif filename.endswith(".tar.xz"):
        decompress.decompress_tar_xz(filepath, target_dir)
    elif filename.endswith(".tar"):
        decompress.decompress_tar(filepath, target_dir)
    else:
        raise RuntimeError("未知的压缩文件格式：" + filename)


def create_archive_from_directory(src_path, archive_name, delete_existing_archive=False):
    if delete_existing_archive and os.path.exists(archive_name):
        log_debug("Removing snapshot file " + archive_name + " before creating new one")
        os.remove(archive_name)

    archive_dir = os.path.dirname(archive_name)
    if not os.path.isdir(archive_dir):
        os.mkdir(archive_dir)

    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(src_path, arcname=os.path.basename(src_path))


def get_url_file_content_length_without_download(url: str, headers=None) -> int:
    """
    不下载获取url上面文件的文件大小
    """
    try:
        resp = requests.head(url, allow_redirects=True, headers=headers, timeout=3000)
        content_length = int(resp.headers.get("content-length"))
    except:
        content_length = -1
    return content_length


def download_from_scp(hostname, username, path, target_path):
    """
    使用scp下载文件
    """
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(hostname=hostname, username=username)
    scpc = scp.SCPClient(ssh.get_transport())
    scpc.get(path, local_path=target_path)


def download_from_http(url, target_path, headers=None, chunk_size=8192):
    """
    使用 http 下载文件
    """
    content_length = get_url_file_content_length_without_download(url)
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(target_path, "wb") as f:
            size = 0
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                size += len(chunk)
                download_progress(size, content_length)
            print()


def download_file(url, local_path, hash_type="SHA256", file_hash=None, force=False):
    """
    分块下载大文件， 带进度条
    :param url: 下载的url
    :param local_path: 本地存储路径
    :param hash_type: 文件的hash类型
    :param file_hash: 文件的hash
    :param force:是否覆盖本地已存在的文件
    :return:
    """

    if not os.path.isdir(local_path):
        os.makedirs(local_path)

    filename = os.path.basename(url)
    target_path = os.path.join(local_path, filename)

    # 如果已经存在则检查HASH是否匹配
    if not check_hash(target_path, hash_type, file_hash):
        log_info("{} 文件的 {} 不匹配，将重新下载".format(target_path, hash_type))
        force = True

    if (not os.path.exists(target_path)) or force:
        log_info("下载 " + url + " 到 " + target_path)
        p = urlparse(url)
        if p.scheme == "ssh":
            download_from_scp(p.hostname, p.username, p.path, local_path)
        else:
            download_from_http(url, target_path, chunk_size=8192)
    else:
        log_info("已经下载，跳过下载 {}".format(url))

    # 检查下载文件的HASH
    if not check_hash(target_path, hash_type, file_hash):
        errorStr = "下载的文件 {} 不匹配: {}({})".format(hash_type, target_path, file_hash)
        log_info(errorStr)
        raise RuntimeError(errorStr)

    return target_path


def clone_git_repository(url, pkg_name, revision, local_path):
    """
    从git仓库下载包
    """
    target_path = escapify_path(os.path.join(local_path, pkg_name))
    target_exists = os.path.exists(target_path)
    log_info("克隆 {} 到 {}".format(url, target_path))

    repo_exists = os.path.exists(os.path.join(target_path, ".git"))

    if not repo_exists:
        if target_exists:
            log_debug("克隆前删除 " + target_path)
            shutil.rmtree(target_path)
        die_if_non_zero(exec_shell("{} clone --recursive {} {}".format(SHELL_GIT, url, target_path)))
    else:
        log_info("仓库 {} 已经存在，将进行拉取".format(target_path))
        die_if_non_zero(exec_shell("{} -C {} fetch --recurse-submodules".format(SHELL_GIT, target_path)))

    if revision is None:
        revision = "HEAD"
    die_if_non_zero(exec_shell("{} -C {} reset --hard {}".format(SHELL_GIT, target_path, revision)))
    die_if_non_zero(exec_shell("{} -C {} clean -fxd".format(SHELL_GIT, target_path)))

    return target_path


def clone_hg_repository(url, pkg_name, revision, local_path):
    """
    从hg仓库下载包
    """
    target_path = escapify_path(os.path.join(local_path, pkg_name))
    target_exists = os.path.exists(target_path)
    log_info("克隆 {} 到 {}".format(url, target_path))

    repo_exists = os.path.exists(os.path.join(target_path, ".hg"))

    if not repo_exists:
        if target_exists:
            log_debug("克隆前删除 " + target_path)
            shutil.rmtree(target_path)
        die_if_non_zero(exec_shell("{} clone {} {}".format(SHELL_HG, url, target_path)))
    else:
        log_info("仓库 {} 已经存在，将进行拉取".format(target_path))
        die_if_non_zero(exec_shell("{} pull -R {}".format(SHELL_HG, target_path)))

    if revision is None:
        revision = "HEAD"
    die_if_non_zero(exec_shell("{} update -R {} -C {}".format(SHELL_HG, target_path, revision)))
    die_if_non_zero(exec_shell("{} purge -R {}  --config extensions.purge=".format(SHELL_HG, target_path)))

    return target_path


def clone_svn_repository(url, pkg_name, local_path):
    """
    从svn仓库下载包
    """
    target_path = escapify_path(os.path.join(local_path, pkg_name))
    target_exists = os.path.exists(target_path)
    log_info("克隆 {} 到 {}".format(url, target_path))

    if target_exists:
        log_debug("克隆前删除 " + target_path)
        shutil.rmtree(target_path)
    die_if_non_zero(exec_shell("{} checkout {} {}".format(SHELL_SVN, url, target_path)))

    return target_path


def extract_file_and_filter(filename, package_path, rm_top_dir=False, include=None, exclude=None):
    """
    提前文件并过滤
    """
    # 先解压到临时文件，然后工具需要复制的包目录
    with tempfile.TemporaryDirectory() as tmpdir:
        extract_file(filename, tmpdir)
        src_dir = tmpdir
        if rm_top_dir:  # 移除顶部目录
            tmp_file_list = os.listdir(tmpdir)
            if len(tmp_file_list) == 1 and os.path.isdir(os.path.join(tmpdir, tmp_file_list[0])):
                src_dir = os.path.join(tmpdir, tmp_file_list[0])
        copy_tree(src_dir, package_path, include=include, exclude=exclude)


def download_package_from_local(package, package_path, force=False):
    pkg_name = package['name']
    pkg_url = package['info'].get('url', None)
    pkg_path = package['info'].get('path', None)
    pkg_include = package['info'].get('include', None)
    pkg_exclude = package['info'].get('exclude', None)
    pkg_path = pkg_path or pkg_url

    if force:
        shutil.rmtree(package_path)
        os.makedirs(package_path)

    if pkg_path is None:
        err_msg = "本地包 {} 的 path 为空".format(pkg_name)
        raise RuntimeError(err_msg)

    copy_tree(pkg_path, package_path, include=pkg_include, exclude=pkg_exclude)


def download_package_from_source_file(package, package_path, force=False):
    pkg_name = package['name']
    pkg_url = package['info'].get('url', None)
    pkg_hash_type = package['info'].get('hash_type', None)
    pkg_file_hash = package['info'].get('file_hash', None)
    pkg_version = package['info'].get('version', '')

    if force:
        shutil.rmtree(package_path)
        os.makedirs(package_path)

    cache_path = os.path.join(CACHE_DIR, pkg_name[0].lower(), pkg_name, pkg_version)
    try:
        cache_file = None
        if type(pkg_url) is list:
            for url in pkg_url:
                try:
                    cache_file = download_file(url, cache_path, pkg_hash_type, pkg_file_hash, force=force)
                    break
                except Exception as e:
                    log_info(str(e))
                    continue
        else:
            cache_file = download_file(pkg_url, cache_path, pkg_hash_type, pkg_file_hash, force=force)

        filename = os.path.basename(pkg_url)
        shutil.copyfile(cache_file, os.path.join(package_path, filename))
    except:
        shutil.rmtree(package_path)
        raise


def download_package_from_archive(package, package_path, force=False):
    pkg_name = package['name']
    pkg_url = package['info'].get('url', None)
    pkg_hash_type = package['info'].get('hash_type', None)
    pkg_file_hash = package['info'].get('file_hash', None)
    pkg_version = package['info'].get('version', '')
    pkg_include = package['info'].get('include', None)
    pkg_exclude = package['info'].get('exclude', None)
    pkg_rm_top_dir = package['info'].get('rm_top_dir', False)

    if force:
        shutil.rmtree(package_path)
        os.makedirs(package_path)

    cache_path = os.path.join(CACHE_DIR, pkg_name[0].lower(), pkg_name, pkg_version)

    cache_file = None
    if type(pkg_url) is list:
        for url in pkg_url:
            try:
                url = url.replace("${version}", pkg_version)
                cache_file = download_file(url, cache_path, pkg_hash_type, pkg_file_hash, force=force)
                break
            except Exception as e:
                log_info(str(e))
                continue
    else:
        url = pkg_url.replace("${version}", pkg_version)
        cache_file = download_file(url, cache_path, pkg_hash_type, pkg_file_hash, force=force)

    if cache_file is None:
        if type(pkg_url) is list:
            url = [url.replace("${version}", pkg_version) for url in pkg_url]
            err_msg = "下载文件失败: {}".format(url)
        else:
            url = pkg_url.replace("${version}", pkg_version)
            err_msg = "下载文件失败: {}".format(url)
        raise RuntimeError(err_msg)

    extract_file_and_filter(cache_file, package_path, pkg_rm_top_dir, include=pkg_include, exclude=pkg_exclude)


def download_package_from_git(package, package_path, force=False):
    pkg_name = package['name']
    pkg_url = package['info'].get('url', None)
    pkg_git_url = package['info'].get('git', None)
    pkg_version = package['info'].get('version', '')
    pkg_include = package['info'].get('include', None)
    pkg_exclude = package['info'].get('exclude', None)
    pkg_revision = package['info'].get('revision', None)
    pkg_git_url = pkg_git_url or pkg_url

    if pkg_git_url is None:
        raise

    shutil.rmtree(package_path, onerror=delete)
    os.makedirs(package_path)

    cache_path = os.path.join(CACHE_DIR, pkg_name[0].lower(), pkg_name, pkg_version)

    # 克隆后压缩缓存
    archive_name = pkg_name + ".tar.gz"
    if pkg_revision is not None:
        archive_name = pkg_name + "_" + pkg_revision + ".tar.gz"
    archive_sha1 = archive_name + ".sha256"
    archive_path = os.path.join(cache_path, archive_name)
    archive_sha1_path = os.path.join(cache_path, archive_sha1)

    # 如果已经存在则检查SHA1是否匹配
    if (not force) and os.path.exists(archive_path) and os.path.exists(archive_sha1_path):
        sha1_hash = open(archive_sha1_path).read()
        hash_file = compute_file_sha256(archive_path)
        if hash_file == sha1_hash:
            log_info("包 {} 已经下载，将使用缓存文件".format(pkg_name))
            extract_file_and_filter(archive_path, package_path, include=pkg_include, exclude=pkg_exclude)
            return

    repo_path = clone_git_repository(pkg_git_url, pkg_name, pkg_revision, cache_path)
    copy_tree(repo_path, package_path, include=pkg_include, exclude=pkg_exclude)
    create_archive_from_directory(repo_path, archive_path, pkg_revision is None)
    hash_file = compute_file_sha256(archive_path)
    with open(archive_sha1_path, 'w') as f:
        f.write(hash_file)
    shutil.rmtree(repo_path, onerror=delete)


def download_package_from_hg(package, package_path, force=False):
    pkg_name = package['name']
    pkg_url = package['info'].get('url', None)
    pkg_hg_url = package['info'].get('hg', None)
    pkg_version = package['info'].get('version', '')
    pkg_revision = package['info'].get('revision', None)
    pkg_include = package['info'].get('include', None)
    pkg_exclude = package['info'].get('exclude', None)
    pkg_hg_url = pkg_hg_url or pkg_url

    if pkg_hg_url is None:
        raise

    shutil.rmtree(package_path, onerror=delete)
    os.makedirs(package_path)

    cache_path = os.path.join(CACHE_DIR, pkg_name[0].lower(), pkg_name, pkg_version)

    # 克隆后压缩缓存
    archive_name = pkg_name + ".tar.gz"
    if pkg_revision is not None:
        archive_name = pkg_name + "_" + pkg_revision + ".tar.gz"
    archive_sha1 = archive_name + ".sha256"
    archive_path = os.path.join(cache_path, archive_name)
    archive_sha1_path = os.path.join(cache_path, archive_sha1)

    # 如果已经存在则检查SHA1是否匹配
    if (not force) and os.path.exists(archive_path) and os.path.exists(archive_sha1_path):
        sha1_hash = open(archive_sha1_path).read()
        hash_file = compute_file_sha256(archive_path)
        if hash_file == sha1_hash:
            log_info("包 {} 已经下载，将使用缓存的包。".format(pkg_name))
            extract_file_and_filter(archive_path, package_path, include=pkg_include, exclude=pkg_exclude)
            return

    repo_path = clone_hg_repository(pkg_hg_url, pkg_name, pkg_revision, cache_path)
    copy_tree(repo_path, package_path, include=pkg_include, exclude=pkg_exclude)
    create_archive_from_directory(repo_path, archive_path, pkg_revision is None)
    hash_file = compute_file_sha256(archive_path)
    with open(archive_sha1_path, 'w') as f:
        f.write(hash_file)
    shutil.rmtree(repo_path, onerror=delete)


def download_package_from_svn(package, package_path, force=False):
    pkg_name = package['name']
    pkg_url = package['info'].get('url', None)
    pkg_svn_url = package['info'].get('svn', None)
    pkg_version = package['info'].get('version', '')
    pkg_include = package['info'].get('include', None)
    pkg_exclude = package['info'].get('exclude', None)
    pkg_svn_url = pkg_svn_url or pkg_url

    if pkg_svn_url is None:
        raise

    shutil.rmtree(package_path, onerror=delete)
    os.makedirs(package_path)

    cache_path = os.path.join(CACHE_DIR, pkg_name[0].lower(), pkg_name, pkg_version)

    # 克隆后压缩缓存
    archive_name = pkg_name + ".tar.gz"
    archive_sha1 = archive_name + ".sha256"
    archive_path = os.path.join(cache_path, archive_name)
    archive_sha1_path = os.path.join(cache_path, archive_sha1)

    # 如果已经存在则检查SHA1是否匹配
    if (not force) and os.path.exists(archive_path) and os.path.exists(archive_sha1_path):
        sha1_hash = open(archive_sha1_path).read()
        hash_file = compute_file_sha256(archive_path)
        if hash_file == sha1_hash:
            log_info("包 {} 已经下载，将使用缓存的包。".format(pkg_name))
            extract_file_and_filter(archive_path, package_path, include=pkg_include, exclude=pkg_exclude)
            return

    repo_path = clone_svn_repository(pkg_svn_url, pkg_name, cache_path)
    copy_tree(repo_path, package_path, include=pkg_include, exclude=pkg_exclude)
    create_archive_from_directory(repo_path, archive_path, True)
    hash_file = compute_file_sha256(archive_path)
    with open(archive_sha1_path, 'w') as f:
        f.write(hash_file)
    shutil.rmtree(repo_path, onerror=delete)


def apply_patch_file(patch_path, src_path, pnum):
    log_info("应用补丁到 " + src_path)
    arguments = "-d " + src_path + " -p" + str(pnum) + " < " + patch_path
    arguments_binary = "-d " + src_path + " -p" + str(pnum) + " --binary < " + patch_path
    res = exec_shell(SHELL_PATCH + " --dry-run " + arguments, quiet=True)
    if res != 0:
        arguments = arguments_binary
        res = exec_shell(SHELL_PATCH + " --dry-run " + arguments, quiet=True)
    if res != 0:
        log_error("补丁程序失败, 这个补丁已经应用过了吗? ")
        exec_shell(SHELL_PATCH + " --dry-run " + arguments)
        exit(255)
    else:
        die_if_non_zero(exec_shell(SHELL_PATCH + " " + arguments, quiet=True))


def run_python_script(script_path, args=""):
    log_info("运行 Python 脚本 " + script_path)
    die_if_non_zero(exec_shell(SHELL_PYTHON + " " + escapify_path(script_path) + " " + args, False))


def post_process(pkg_name, package_dir, patches_dir, post):
    if post is None:
        return 0

    if 'type' not in post:
        log_error("无效的格式 {}, 'post_process'必须包含 'type' ".format(pkg_name))
        return -1
    if 'file' not in post:
        log_error("无效的格式 {}, 'post_process'必须包含 'file' ".format(pkg_name))
        return -1

    post_type = post['type']
    post_file = post['file']

    if post_type == "patch":
        patch_path = os.path.join(patches_dir, post_file)
        apply_patch_file(patch_path, package_dir, post.get('pnum', DEFAULT_PNUM))
    elif post_type == "script":
        script_path = os.path.join(patches_dir, post_file)
        run_python_script(script_path, pkg_name + " \"" + package_dir + "\"")
    else:
        log_error("{} 未知的 post_process 类型 {}".format(pkg_name, post_type))
        return -1


# 解析命令行参数
def parser_argument(argv=None):
    parser = argparse.ArgumentParser(description='vcspm.py v%s - C++ Package Manager.' % version.__version__,
                                     formatter_class=HelpFormatter)

    parser.add_argument(
        '--service-url', '-s',
        help='包仓库地址',
        default=None,
        metavar='url')

    parser.add_argument(
        '--install-dir', '-i',
        help='包安装目录',
        default=None,
        metavar='dir')

    parser.add_argument(
        '--patches-dir', '-p',
        help='补丁安装目录',
        default=None,
        metavar='dir')

    parser.add_argument(
        '--vcspm-file', '-f',
        help='指定包信息文件',
        default=None,
        metavar='file')

    parser.add_argument(
        '--root', '-r',
        help='指定项目根目录',
        default=None,
        metavar='dir')

    parser.add_argument(
        '--list', '-l',
        help='列出全部可用的包',
        action="store_true")

    parser.add_argument(
        '--require',
        help='获取指定的包',
        action="extend",
        nargs="*",
        metavar='pkg',
        default=[])

    parser.add_argument(
        '--skip',
        help='跳过指定的包',
        action="extend",
        nargs="*",
        metavar='pkg',
        default=[])

    parser.add_argument(
        '--clean', '-c',
        help='获取之前清除指定的包',
        action="extend",
        nargs="*",
        metavar='pkg',
        default=[])

    parser.add_argument(
        '--clean-all', '-C',
        help='获取之前清除全部包',
        action="store_true")

    parser.add_argument(
        '--debug',
        help='输出调试信息',
        action="store_true")

    parser.add_argument(
        '--break-on-error',
        help='出现错误立即中断获取',
        action="store_true")

    args = parser.parse_args(argv)
    print('vcspm.py v%s' % version.__version__)

    return args


def main(argv=None):
    global debug_output

    args = parser_argument(argv)

    if args.debug is not None:
        debug_output = args.debug

    root_dir = args.root or ROOT_DIR
    patches_dir = args.patches_dir or PATCHES_DIR
    vcspm_filename = args.vcspm_file or VCSPM_FILE

    patches_dir = os.path.join(root_dir, patches_dir)
    vcspm_filepath = os.path.abspath(os.path.join(root_dir, vcspm_filename))

    state_filename = "." + vcspm_filename
    state_filepath = os.path.join(root_dir, state_filename)

    log_debug("vcspm_filename = " + vcspm_filepath)
    log_debug("state_filename    = " + state_filepath)

    # 读取依赖包文件
    vcspm = readJsonData(vcspm_filepath)
    if vcspm is None:
        return -1

    vcspm_state = {}
    if os.path.exists(state_filepath):
        vcspm_state = readJsonData(state_filepath) or {}

    # 包安装目录
    if args.install_dir is None:
        install_dir = vcspm.get("install_dir", INSTALL_DIR)
    else:
        install_dir = args.install_dir

    # 包服务器地址
    if args.service_url is None:
        service_url = vcspm.get("service_url", INSTALL_DIR)
    else:
        service_url = args.service_url

    # 创建根目录
    if not os.path.isdir(root_dir):
        log_info("创建根目录: " + root_dir)
        os.mkdir(root_dir)

    # 创建包目录
    install_path = os.path.join(root_dir, install_dir)
    if not os.path.isdir(install_path):
        log_info("创建包安装目录: " + install_path)
        os.mkdir(install_path)

    # 创建缓存目录
    if not os.path.isdir(CACHE_DIR):
        log_info("创建缓存目录: " + CACHE_DIR)
        os.mkdir(CACHE_DIR)

    package_list = vcspm.get("packages") or {}

    # 列出包
    if args.list:
        list_packages(package_list)
        return 0

    # 状态文件中的包信息
    state_package_list = vcspm_state.get("packages")
    if state_package_list is None:
        vcspm_state["packages"] = {}
        state_package_list = vcspm_state.get("packages")

    # 删除已经移除的包状态
    pkg_names = package_list.keys()
    pkg_state_names = list(state_package_list.keys())
    for pkg_name in pkg_state_names:
        if pkg_name not in pkg_names:
            log_info("删除已经移除的包状态: " + pkg_name)
            state_package_list.pop(pkg_name)
    writeJsonData(vcspm_state, state_filepath)

    # 删除已经移除的包目录
    for pkg_name in os.listdir(install_path):
        if pkg_name not in pkg_names:
            log_info("删除已经移除的包: " + pkg_name)
            shutil.rmtree(os.path.join(install_path, pkg_name), onerror=delete)

    failed_packages = []  # 失败的包
    for pkg_name in pkg_names:
        info = package_list.get(pkg_name)

        # 跳过--skip指定的包
        if args.skip and (pkg_name in args.skip):
            continue

        # 不是--require指定的包
        if args.require and (pkg_name not in args.require):
            continue

        package_dir = os.path.join(install_path, pkg_name)
        package_dir = package_dir.replace(os.path.sep, '/')
        patch_dir = os.path.join(patches_dir, pkg_name)
        patch_dir = patch_dir.replace(os.path.sep, '/')

        log_debug("********** PACKAGE " + pkg_name + " **********")
        log_debug("package_dir = " + package_dir + ")")

        # 检查包是否已经缓存
        cached_state = False
        if (pkg_name not in args.clean) and (not args.clean_all):
            for sname in state_package_list.keys():
                sinfo = state_package_list.get(sname)
                if sinfo == info:
                    cached_state = True
                    break

        if cached_state:
            log_info("跳过已经缓存的包：{}".format(pkg_name))
            continue
        else:
            # 删除缓存的包信息
            if pkg_name in state_package_list.keys():
                state_package_list.pop(pkg_name)

        # 清除包目录
        clean_package = False
        if args.clean_all or (pkg_name in args.clean):
            log_info("清除包 {} 目录".format(pkg_name))
            clean_package = True
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir, onerror=delete)

        # 创建包目录
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)

        try:
            if type(info) is str:  # 使用仓库
                pkg_version = info
                info = get_package_info_from_repository(service_url, pkg_name, pkg_version, patch_dir)
                if info is None:
                    err_msg = "无法获取包 {} 信息".format(pkg_name)
                    log_error(err_msg)
                    raise RuntimeError(err_msg)

            if 'type' not in info:
                err_msg = "未指定包 {} 的类型".format(pkg_name)
                log_error(err_msg)
                raise RuntimeError(err_msg)

            package_type = info['type']
            package = {'name': pkg_name, 'info': info}
            if package_type == "local":
                download_package_from_local(package, package_dir, clean_package)
            elif package_type == "sourcefile":
                download_package_from_source_file(package, package_dir, clean_package)
            elif package_type == "archive":
                download_package_from_archive(package, package_dir, clean_package)
            elif package_type == "git":
                download_package_from_git(package, package_dir, clean_package)
            elif package_type == "hg":
                download_package_from_hg(package, package_dir, clean_package)
            elif package_type == "svn":
                download_package_from_svn(package, package_dir, clean_package)
            else:
                raise ValueError("不支持的包类型： " + package_type)

            # 更新后需要执行的任务
            post = info.get('post_process', None)
            post_process(pkg_name, package_dir, patch_dir, post)

            # 更新状态文件
            state_package_list[pkg_name] = info
            writeJsonData(vcspm_state, state_filepath)
        except:
            log_error("更新包 {} 失败，(reason: {})".format(pkg_name, sys.exc_info()[0]))
            shutil.rmtree(package_dir, onerror=delete)
            if args.break_on_error:
                exit(-1)
            traceback.print_exc()
            failed_packages.append(pkg_name)

    if failed_packages:
        log_info("***************************************")
        log_info("下列包更新失败:")
        log_info(', '.join(failed_packages))
        log_info("***************************************")
        return -1

    # 更新修改时间
    os.utime(state_filepath, None)
    log_info("更新包完成")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

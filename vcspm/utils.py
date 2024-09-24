import hashlib
import os
import shutil
import stat
import subprocess
import tarfile
from pathlib import Path
import platform

from vcspm.logger import logging

SHELL_PATCH = "patch"
SHELL_PYTHON = "python"


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


def create_archive_from_directory(src_path, archive_name, delete_existing_archive=False):
    if delete_existing_archive and os.path.exists(archive_name):
        logging.debug("Removing snapshot file " + archive_name + " before creating new one")
        os.remove(archive_name)

    archive_dir = os.path.dirname(archive_name)
    if not os.path.isdir(archive_dir):
        os.makedirs(archive_dir)

    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(src_path, arcname=os.path.basename(src_path))


# 执行命令
def exec_shell(command, quiet=False):
    out = None
    err = None

    if quiet:
        out = subprocess.DEVNULL
        err = subprocess.STDOUT

    logging.debug("> " + command)

    return subprocess.call(command, shell=True, stdout=out, stderr=err)


def die_if_non_zero(res):
    if res != 0:
        raise ValueError("命令返回非零状态: " + str(res))


def delete(func, path, execinfo):
    os.chmod(path, stat.S_IWUSR)
    func(path)


# 转义路径
def escapify_path(path):
    if path.find(" ") == -1:
        return path
    if platform.system() == "Windows":
        return "\"" + path + "\""
    return path.replace("\\ ", " ")


def apply_patch_file(patch_path, src_path, pnum):
    logging.info("应用补丁到 " + src_path)
    arguments = "-d " + src_path + " -p" + str(pnum) + " < " + patch_path
    arguments_binary = "-d " + src_path + " -p" + str(pnum) + " --binary < " + patch_path
    res = exec_shell(SHELL_PATCH + " --dry-run " + arguments, quiet=True)
    if res != 0:
        arguments = arguments_binary
        res = exec_shell(SHELL_PATCH + " --dry-run " + arguments, quiet=True)
    if res != 0:
        logging.error("补丁程序失败, 这个补丁已经应用过了吗? ")
        exec_shell(SHELL_PATCH + " --dry-run " + arguments)
        exit(255)
    else:
        die_if_non_zero(exec_shell(SHELL_PATCH + " " + arguments, quiet=True))


def run_python_script(script_path, args=""):
    logging.info("运行 Python 脚本 " + script_path)
    die_if_non_zero(exec_shell(SHELL_PYTHON + " " + escapify_path(script_path) + " " + args, False))

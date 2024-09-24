import os
import shutil
import tempfile

from vcspm import decompress
from vcspm.logger import logging
from vcspm.utils import copy_tree


def extract_file(filepath, target_dir):
    """
    解压文件
    :param filepath: 压缩包
    :param target_dir: 解压路径
    :return:
    """
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    logging.info("解压缩 " + filepath)
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
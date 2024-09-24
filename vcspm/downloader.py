import os
from urllib.parse import urlparse

import paramiko
import requests
import scp

from vcspm import utils
from vcspm.logger import logging


def _get_url_file_content_length(url: str, headers=None) -> int:
    """
    不下载获取url上面文件的文件大小
    """
    try:
        resp = requests.head(url, allow_redirects=True, headers=headers, timeout=3000)
        content_length = int(resp.headers.get("content-length"))
    except:
        content_length = -1
    return content_length


def _download_from_scp(hostname, username, path, target_path):
    """
    使用scp下载文件
    """
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(hostname=hostname, username=username)
    scpc = scp.SCPClient(ssh.get_transport())
    scpc.get(path, local_path=target_path)


# #下载进度条
def _download_progress(cur_size, total_size):
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


def _download_from_http(url, target_path, headers=None, chunk_size=8192):
    """
    使用 http 下载文件
    """
    content_length = _get_url_file_content_length(url)
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(target_path, "wb") as f:
            size = 0
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                size += len(chunk)
                _download_progress(size, content_length)
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
    target_path = str(os.path.join(local_path, filename))

    # 如果已经存在则检查HASH是否匹配
    if not utils.check_hash(target_path, hash_type, file_hash):
        logging.info("{} 文件的 {} 不匹配，将重新下载".format(target_path, hash_type))
        force = True

    if (not os.path.exists(target_path)) or force:
        logging.info("下载 " + url + " 到 " + target_path)
        p = urlparse(url)
        if p.scheme == "ssh":
            _download_from_scp(p.hostname, p.username, p.path, local_path)
        else:
            _download_from_http(url, target_path, chunk_size=8192)
    else:
        logging.info("已经下载，跳过下载 {}".format(url))

    # 检查下载文件的HASH
    if not utils.check_hash(target_path, hash_type, file_hash):
        errorStr = "下载的文件 {} 不匹配: {}({})".format(hash_type, target_path, file_hash)
        logging.info(errorStr)
        raise RuntimeError(errorStr)

    return target_path

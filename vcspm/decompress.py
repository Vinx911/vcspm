import bz2
import gzip
import lzma
import os
import tarfile
import zipfile
import py7zr


def decompress_zip(filename, target_dir):
    """ 解压缩ZIP文件 """
    zfile = zipfile.ZipFile(filename)
    os.makedirs(target_dir, exist_ok=True)
    zfile.extractall(target_dir)
    zfile.close()


def decompress_gzip(filename, target_dir):
    """ 解压缩GZIP文件 """
    fname = filename.replace(".gz", "")
    gfile = gzip.GzipFile(filename)
    os.makedirs(target_dir, exist_ok=True)
    target_file = open(os.path.join(target_dir, fname), "wb+")
    target_file.write(gfile.read())
    gfile.close()
    target_file.close()


def decompress_bz2(filename, target_dir):
    """ 解压缩BZIP2文件 """
    fname = filename.replace(".bz2", "")
    zfile = bz2.BZ2File(filename)  # open the file
    os.makedirs(target_dir, exist_ok=True)
    target_file = open(os.path.join(target_dir, fname), "wb+")
    target_file.write(zfile.read())
    zfile.close()
    target_file.close()


def decompress_xz(filename, target_dir):
    """ 解压缩XZ文件 """
    fname = filename.replace(".xz", "")
    zfile = lzma.open(filename)  # open the file
    os.makedirs(target_dir, exist_ok=True)
    target_file = open(os.path.join(target_dir, fname), "wb+")
    target_file.write(zfile.read())
    zfile.close()
    target_file.close()


def decompress_tar(filename, target_dir):
    """ 解压缩tar文件 """
    tar = tarfile.open(filename)
    os.makedirs(target_dir, exist_ok=True)
    tar.extractall(target_dir)
    tar.close()


def decompress_7z(filename, target_dir):
    """ 解压缩7Z文件 """
    archive = py7zr.SevenZipFile(filename, mode='r')
    archive.extractall(path=target_dir)
    archive.close()


def decompress_tar_gz(filename, target_dir):
    """ 解压缩tar.gz文件 """
    decompress_tar(filename, target_dir)


def decompress_tar_bz2(filename, target_dir):
    """ 解压缩tar.bz2文件 """
    decompress_tar(filename, target_dir)


def decompress_tar_xz(filename, target_dir):
    """ 解压缩tar.xz文件 """
    fname = filename.replace(".xz", "")
    zfile = lzma.open(filename)  # open the file
    os.makedirs(target_dir, exist_ok=True)
    tmpfname = os.path.join(target_dir, "tmp_" + fname)
    target_file = open(tmpfname, "wb+")
    target_file.write(zfile.read())
    zfile.close()
    target_file.close()

    decompress_tar(tmpfname, target_dir)
    os.remove(tmpfname)

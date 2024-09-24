import argparse
import os
import shutil
import sys
import traceback

import logger
import version
import manager
from logger import logging
from vcspm import utils
from vcspm.param import Param

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


# 列出全部包
def list_packages(packages):
    for _, pkg in packages.items():
        if pkg.version is None:
            print("{}".format(pkg.name))
        else:
            print("{}/{}".format(pkg.name, pkg.version))


# 解析命令行参数
def parser_argument(argv=None):
    parser = argparse.ArgumentParser(description='vcspm.py v%s - C++ Package Manager.' % version.__version__,
                                     formatter_class=HelpFormatter)

    parser.add_argument(
        '--repository-url', '-s',
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
    args = parser_argument(argv)

    if args.debug is not None:
        logging.level = logger.Level.DEBUG

    if args.root is not None:
        Param.root_dir = args.root

    if args.patches_dir is not None:
        Param.patches_dir = args.patches_dir

    if args.vcspm_file is not None:
        Param.vcspm_file = args.vcspm_file

    state_filename = "." + Param.vcspm_file

    vcspm_filepath = os.path.abspath(os.path.join(Param.root_dir, Param.vcspm_file))
    state_filepath = os.path.abspath(os.path.join(Param.root_dir, state_filename))
    patches_dir = os.path.abspath(os.path.join(Param.root_dir, Param.patches_dir))

    logging.debug("vcspm_filename = " + vcspm_filepath)
    logging.debug("state_filename = " + state_filepath)

    # 读取依赖包文件
    vcspm = manager.fromJson(vcspm_filepath)
    if vcspm is None:
        return -1

    # 包安装目录
    if args.install_dir is not None:
        Param.install_dir = args.install_dir
    else:
        Param.install_dir = vcspm.install_dir

    # 包服务器地址
    if args.repository_url is not None:
        Param.repository_url = args.repository_url
    else:
        Param.repository_url = vcspm.repository_url

    # 创建根目录
    if not os.path.isdir(Param.root_dir):
        logging.info("创建根目录: " + Param.root_dir)
        os.makedirs(Param.root_dir)

    # 创建包目录
    Param.install_path = utils.escapify_path(os.path.join(Param.root_dir, Param.install_dir))
    if not os.path.isdir(Param.install_path):
        logging.info("创建包安装目录: " + Param.install_path)
        os.makedirs(Param.install_path)


    print("BBBBBBBBBBBBB")
    print(Param.install_path)

    # 创建缓存目录
    if not os.path.isdir(Param.cache_dir):
        logging.info("创建缓存目录: " + Param.cache_dir)
        os.makedirs(Param.cache_dir)

    # 列出包
    if args.list:
        list_packages(vcspm.packages)
        return 0

    # 读取状态文件
    vcspm_state = None
    if os.path.exists(state_filepath):
        vcspm_state = manager.fromJson(state_filepath)

    if vcspm_state is None:
        vcspm_state = manager.Manager()

    # 删除已经移除的包状态
    pkg_names = vcspm.package_names()
    pkg_state_names = vcspm_state.package_names()
    for pkg_name in pkg_state_names:
        if pkg_name not in pkg_names:
            logging.info("删除已经移除的包状态: " + pkg_name)
            vcspm_state.remove(pkg_name)
    vcspm_state.toJson(state_filepath)

    # 删除已经移除的包目录
    for pkg_name in os.listdir(Param.install_path):
        if pkg_name not in pkg_names:
            logging.info("删除已经移除的包: " + pkg_name)
            shutil.rmtree(os.path.join(Param.install_path, pkg_name), onerror=utils.delete)

    failed_packages = []  # 失败的包
    for pkg_name, pkg in vcspm.packages.items():
        # 跳过--skip指定的包
        if args.skip and (pkg_name in args.skip):
            continue

        # 不是--require指定的包
        if args.require and (pkg_name not in args.require):
            continue

        package_dir = os.path.join(Param.install_path, pkg_name)

        logging.debug("********** PACKAGE " + pkg_name + " **********")
        logging.debug("package_dir = " + package_dir + ")")

        # 检查包是否已经缓存
        cached_state = False
        if (pkg_name not in args.clean) and (not args.clean_all):
            spkg = vcspm_state.packages.get(pkg_name)
            if spkg == pkg:
                cached_state = True

        if cached_state:
            logging.info("跳过已经缓存的包：{}".format(pkg.name))
            continue
        else:
            # 删除缓存的包信息
            vcspm_state.remove(pkg.name)

        # 清除包目录
        clean_package = False
        if args.clean_all or (pkg.name in args.clean):
            logging.info("清除包 {} 目录".format(pkg.name))
            clean_package = True
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir, onerror=utils.delete)

        # 创建包目录
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)

        try:
            pkg.download()
            # 更新后需要执行的任务
            pkg.post_process()

            # 更新状态文件
            vcspm_state.packages[pkg_name] = pkg
            vcspm_state.toJson(state_filepath)
        except:
            logging.error("更新包 {} 失败，(reason: {})".format(pkg_name, sys.exc_info()[0]))
            shutil.rmtree(package_dir, onerror=utils.delete)
            if args.break_on_error:
                exit(-1)
            traceback.print_exc()
            failed_packages.append(pkg_name)

    if failed_packages:
        logging.info("***************************************")
        logging.info("下列包更新失败:")
        logging.info(', '.join(failed_packages))
        logging.info("***************************************")
        return -1

    # 更新修改时间
    os.utime(state_filepath, None)
    logging.info("更新包完成")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

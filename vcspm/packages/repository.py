from vcspm.package import Package


class RepositoryPackage(Package):

    def __init__(self, name, info):
        self.pkgName = name
        self.pkgVersion = info

import platform


def check(platforms):
    return platform.system() in platforms

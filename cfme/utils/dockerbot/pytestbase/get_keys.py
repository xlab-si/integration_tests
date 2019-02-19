#!/usr/bin/env python2
import subprocess
import sys

from cfme.utils import conf


def main():
    key_list = [key[-9:].replace(' ', '') for key in conf['gpg']['allowed_keys']]
    proc = subprocess.Popen(
        ['gpg', '--recv-keys', '--keyserver', 'keys.fedoraproject.org'] + key_list)
    proc.wait()
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()

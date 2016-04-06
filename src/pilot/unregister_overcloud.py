#!/usr/bin/python
from register_overcloud import RegisterOvercloud


if __name__ == "__main__":
    ro = RegisterOvercloud()
    ro.unregister_nodes()

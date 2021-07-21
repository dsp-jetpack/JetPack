import logging

def log_setup(log_file='default.log', debug=''):
    """ 
    log setup along with log file and level.

    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(filename=log_file, level=log_level,
                        format=("[%(levelname)s] %(name)s "
                                "%(funcName)s(): %(message)s"))
    logging.info('setting log file as: {}'.format(log_file))
    sh = logging.StreamHandler()
    sh_formatter = logging.Formatter("%(message)s")
    sh.setFormatter(sh_formatter)
    logging.getLogger().addHandler(sh)

def main():
    pass


if __name__ == "__main__":
    main()

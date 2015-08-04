class Node_Conf():
    '''
    holds the network etc. related settings for the nodes (content of cluster.properties)
    '''


    def __init__(self , json):
        self.is_sah = None
        self.is_foreman  = None
        self.is_ceph = None
        self.hostname = None
        self.idrac_ip = None
        self.root_password = None
        self.public_ip = None
        self.public_gateway = None
        self.public_bond = None
        self.public_netmask = None
        self.public_slaves = None
        self.provisioning_ip    = None
        self.provisioning_ip    = None
        self.provisioning_gateway    = None
        self.provisioning_bond    = None
        self.provisioning_netmask    = None
        self.provisioning_slaves    = None
        self.name_server    = None

        self.__dict__ = json
        
        
        
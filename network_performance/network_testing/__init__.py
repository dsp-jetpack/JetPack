import netvaltest
#import netperftest


def run_netvaltest():
    """ entry point for network validation tool """    
    netvaltest.Main()

# XXX(mikeyp) disable since netperftest depends on importlib, which is not in 
# Python 2.6
#def run_netperftest():
#    """ entry point for network performance tool """    
#    netperftest.Main()

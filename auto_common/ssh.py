import subprocess, paramiko, sys
import logging
logger = logging.getLogger(__name__)

class Ssh():

    @staticmethod
    def execute_command(address, usr, pwd, command):
        try :
            logger.info ( "ssh @" + address + ", running : " + command )
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
            os = sys.platform
            
            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.read(), ss_stderr.read()
            logger.info("error :: " + r_err)
            if len(r_err) > 5 :
                logger.error(r_err)
            else:
                logger.info(r_out)
            client.close()
        except IOError :
            logger.warning( ".. host "+ address + " is not up")
            return "host not up"
            
            
        return r_out, r_err

    @staticmethod
    def execute_command_readlines(address, usr, pwd, command):
        try :
            logger.info ( "ssh @" + address + ", running : " + command )
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            os = sys.platform

            client.connect(address, username=usr, password=pwd)
            stdin, ss_stdout, ss_stderr = client.exec_command(command)
            r_out, r_err = ss_stdout.readlines(), ss_stderr.read()
            logger.info("error :: " + r_err)
            if len(r_err) > 5 :
                logger.error(r_err)
            else:
                logger.info(r_out)
            client.close()
        except IOError :
            logger.warning( ".. host "+ address + " is not up")
            return "host not up"


        return r_out, r_err
    

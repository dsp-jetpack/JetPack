import paramiko 

class Scp():
    
 
    @staticmethod
    def put_file(adress, user, passw, localfile, remotefile):
        
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        trans = paramiko.Transport((adress, 22))
        trans.connect(username = user, password = passw)
        sftp = paramiko.SFTPClient.from_transport(trans)
        sftp.put(localfile, remotefile)
        sftp.close()
        trans.close()
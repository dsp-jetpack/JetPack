import re

class FileHelper():
    
    @staticmethod
    def replaceExpression(fileref, searchExp,replaceExp):
        fh = open(fileref, 'r')
        content = fh.readlines() #Dont try this on large files..
        fh.close()
        updated = []
        
        for line in content:
            line = re.sub(searchExp,replaceExp, line)
            updated.append(line)
         
        f_out = file(fileref, 'wb')   
        
        f_out.writelines(updated)
        f_out.close()
        
        
        
    @staticmethod
    def replaceExpressionTXT(fileref, searchExp,replaceExp):
        fh = open(fileref, 'r')
        content = fh.readlines() #Dont try this on large files..
        fh.close()
        updated = []
        
        for line in content:
            line = re.sub(searchExp,replaceExp, line)
            updated.append(line)
         
        f_out = file(fileref, 'w')   
        
        f_out.writelines(updated)
        f_out.close()
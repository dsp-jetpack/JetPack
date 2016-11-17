import importlib
import xlsxwriter
import os, re, time

from auto_common import *

'''def write_columns(list, start_line, column):
    for each in list:
        row = int(list.index(each) + start_line)
        #print row
        #for col in range(0, 1):
        #   print col
        worksheet.write(row, column, str(each))
'''

class ReportBuilder():

    def getHeaders(self, results_file):
        # Open a text file with autofilter example data.
        textfile = open(results_file)
        # Read the headers from the first line of the input file.
        line1 = textfile.readline()
        #print line1
        ma = re.search("\[\[\[(.+)\]\]\]", line1)
        if ma:
            headers = ma.group(1)
            
        return headers
        
    def copyJobHistoryFiles(self, job_history_ip, history_location, job_id):
        cmd = 'sudo -u hdfs hadoop fs -get '+history_location+'' + job_id + '_conf.xml /tmp/'+job_id
        #print cmd
        cmd1 = 'mkdir /tmp/'+job_id
        cmd2 = 'chmod 777 /tmp/'+job_id
        out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd1)
        #print cmd1
        out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd2)
        #print cmd2
        out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd)
        #print cmd
        
        remotefile = '/tmp/'+job_id+'/'+job_id+'_conf.xml'
        #print remotefile
        localfile = job_id+'_conf.xml'
        #print localfile

        #** put this back in after Report testing.
        Scp.get_file(job_history_ip, 'root', 'Ignition01', localfile, remotefile)
        #print out
        #print err
        
    def copyTPCLogFile(self, tpc_location_ip, tpc_file_name):
        Scp.get_file(tpc_location_ip, 'root', 'Ignition01', tpc_file_name, tpc_file_name)
        

    def getConfigParams(self, job_id, params):
        config_params = []
        my_file = job_id+'_conf.xml'
        #print my_file
        
        textfile = open(my_file)
        #params = config.params
        for line in textfile:
            for p in params:
                if '<name>'+p+'</name>' in line:
                    #print line
                    ma = re.search("value>(.+)</value", line)
                    if ma:
                        param = ma.group(1)
                        #print param
                        config_params.append(dict({p:param}))
        return config_params

    def writeConfigParams(self, config_params, worksheet):
        row = 1
        for each in config_params:
            #print each.keys()[0]
            #print each.values()[0]
            worksheet.write(row, 0, str(each.keys()[0]))
            worksheet.write(row, 1, str(each.values()[0]))
            row += 1

    def writeJobLogInfo(self, job_ids, worksheet, containers):
    
        job_file = open('jobLog.log')
        #row, col = 0
        #rows = ['B30', 'B31', 'B32']
        #print containers
        row = 29
        #print job_file
        #print job_ids
        for line in job_file:
            #print line
            for job in job_ids:
                #print 'job: ' + str(job)
                if job in line:
                    #print line
                    row_data = line.split(' ')
                    #print row_data
                    for each in row_data:
                        #print each
                        if row_data.index(each) == 0:
                            row_data[0] = each + ' ' + str('(max containers = '+containers[job_ids.index(job)]+')')
                            #print each
                    #print row_data
                    worksheet.write_row(row, 0, row_data)
                    row += 1
    @staticmethod
    def getTPCResults(results_log, sf):
        run_results = []
        sf_int = []
        textfile = open(results_log)
        for line in textfile:
            #print line
            #time.sleep(1)
            if 'Performance Metric' in line:
                #time.sleep(3)
                ma = re.search(": (.+) ", line)
                if ma:
                    sf_result = ma.group(1)
                    if sf_result == 'NA':
                        run_results.append(str(sf_result))
                        sf_int.append(sf_result)
                    else:
                        sf_int.append(sf_result)
                        run_results.append(str(sf_result) + ' @' + sf)
        #print run_results
        # start_line = 36
        # row = start_line
        # for each in run_results:
            # print each
            # worksheet.write(row, 5, str(each))
            # row += 1
        return sf_int, run_results

    def writeMetrics(self, worksheet):
        metrics = ('time',
                   'CPU',
                   'NW KB/s IN',
                   'NW KB/s OUT',
                   'Mem GB',
                   'Dthruput MB/s Reads',
                   'Dthruput MB/s Writes')

        start_line = 35
        for each in metrics:
            row = int(metrics.index(each) + start_line)
            #print row
            #for col in range(0, 1):
            #   print col
            worksheet.write(row, 0, str(each))

    def writeTsphHeaders():
        start_line = 35
        run_info = ('TSph', 'Run 1', 'Run 2')
        #for each in run_info:
        #    row = int(run_info.index(each) + start_line)
        #    worksheet.write(row, 4, str(each), bold)
        write_columns(run_info, 35, 4)


    def getJobInformation(self, results_file):
    
        time_info = []
        job_info = []
        job_ids = []
        containers = []

        textfile = open(results_file)
        for line in textfile:
            #print line
            if 'JobID' in line and ('gen' in line or 'Gen' in line):
                #print line
                # Split the input data based on whitespace.
                ma = re.search("JobID: (.+)", line)
                if ma:
                    job_id = ma.group(1) 
                job = 'Gen ' + str(job_id)
                #print job
                #print job_id
                job_info.append(job)
                job_ids.append(job_id)

            if 'JobID' in line and ('sort' in line or 'Sort' in line):
                # Split the input data based on whitespace.
                ma = re.search("JobID: (.+)", line)
                if ma:
                    job_id = ma.group(1) 
                job = 'sort ' + str(job_id)
                job_info.append(job)
                job_ids.append(job_id)

            if 'JobID' in line and ('validate' in line or 'Validate' in line):
                # Split the input data based on whitespace.
                ma = re.search("JobID: (.+)", line)
                if ma:
                    job_id = ma.group(1) 
                job = 'validate ' + str(job_id)
                job_info.append(job)
                job_ids.append(job_id)
                #for each in row_data:
                #    print each
                #print row_data[-1]
                #worksheet.write_row('A19', row_data[-1])
            if 'runtime' in line and ('Gen' in line or 'gen' in line):
                line = line.split(' | ')
                runtime = line[-1]
                ma = re.search("\((.+) seconds", runtime)
                if ma:
                    runtime = ma.group(1)
                    #print runtime
                time_info.append(runtime)
            if 'runtime' in line and ('Sort' in line or 'sort' in line):
                line = line.split(' | ')
                runtime = line[-1]
                ma = re.search("\((.+) seconds", runtime)
                if ma:
                    runtime = ma.group(1)
                    #print runtime
                time_info.append(runtime)
            if 'runtime' in line and ('Validate' in line or 'validate' in line):
                line = line.split(' | ')
                runtime = line[-1]
                ma = re.search("\((.+) seconds", runtime)
                if ma:
                    runtime = ma.group(1)
                    #print runtime
                time_info.append(runtime)

            if '| Max Containers |' in line:
                #print line
                #time.sleep(2)
                line = line.split(' | ')
                value = line[-1]
                containers.append(value)
            #else:
            #    if containers
            #    containers.append('0.0')

        return time_info, job_info, job_ids, containers


    def getMetric(self, job, node, metric, results_file):
        config = importlib.import_module('config_reports')
        # results_file = config.results_file # 'SF1-3 resultsB.txt'
        value = []
        textfile = open(results_file)

        for line in textfile:
            #print line
            #time.sleep(1)
            if job in line and node in line and metric in line:
                #print 'found string'
                #print line
                #time.sleep(3)
                #print job, node, metric
                #else:
                # Split the input data based on 'bar'.
                row_data = line.split(' | ')
                #for each in row_data:
                #    print each
                    #value.append(each)
                #print row_data[-1]
                value = []
                value.append(row_data[-1])
                #print row_data[-1]
                #print len(value)
                #time.sleep(1)
                #print 'value: ' +str(value)
                #return value

            else:
                if len(value) == 0:
                    #print line
                    #print 'empty line'
                    value = [0]
                    #print job, node, metric
                    #return value

             #print len(value)

             #if len(value) > 0:
             #   return value
             #else:
             #    value.append(0)
        return value

    def getSF(self, job, node, metric, results_file):
        config = importlib.import_module('config_reports')
        #results_file = config.results_file # 'SF1-3 resultsB.txt'
        location = config.report_location
        value = []
        #results_file = '/'+ location + '/' + results_file
        #print results_file
        textfile = open(results_file)
        #time.sleep(1)
        print 'searching for SF in: '
        #print job, node, metric, results_file
        #time.sleep(1)
        for line in textfile:
            if job in line and node in line and metric in line:
                #print line
                #time.sleep(1)
                # Split the input data based on 'bar'.
                row_data = line.split(' | ')
                #print row_data[2]
                value.append(row_data[2])
            
        return value[0]
        
    def convertRowToSF(self, row_size):

        if row_size == '10000000000':
            row_size = 'SF1'
        elif row_size == '30000000000':
            row_size = 'SF3'
        elif row_size == '100000000000':
            row_size = 'SF10'
        elif row_size == '300000000000':
            row_size = 'SF30'
        elif row_size == '1000000000000':
            row_size = 'SF100'
        else:
            row_size = row_size

        return row_size
        
    def getResourceMetrics(self, worksheet, results_file):
        cdh_config = importlib.import_module('config_cdh5')
        config = importlib.import_module('config_reports')
        tpc_flag = cdh_config.tpc_flag
        node = config.node
        xbb_flag = cdh_config.xbb_flag
        if tpc_flag == 'true':
            jobs = ('TPC-HSGen', 'TPC-HSSort', 'TPC-HSValidate')
        elif xbb_flag == 'true':
            jobs = ('to', 'be', 'decided')
        else:
            jobs = ('gen', 'sort', 'validate')
        metrics = ('CPU Total', 'bytes_in', 'bytes_out', 'physical_memory_used', 'total_read_bytes_rate_across_disks', 'total_write_bytes_rate_across_disks')
        
        row = 36
        for metric in metrics:
            col = 1
            for job in jobs:
                bytes = ['bytes', 'KBs', 'MBs', 'GBs', 'TBs']
                size = 0
                value = float(self.getMetric(job, node, metric, results_file)[0])
                #print metric
                #print value
                if metric != 'CPU Total':
                    while float(value) > 1024:
                        value = value/1024
                        size += 1
                        #print value
                    #print bytes[size]
                    value = round(value, 2)
                    value = str(value) + ' ' + str(bytes[size])
                else:
                    value = round(value, 2)
                    value = str(value) + ' %'
                worksheet.write(row, col, str(value))
                col += 1
            row += 1
        #time.sleep(3)
        #print job, node, metric, results_file
        #time.sleep(3)
        scale_factor = self.getSF(job, node, metric, results_file)

        if scale_factor == '100GB':
            scale_factor = 'SFA (100GB)'
            sf = 'SFA'
        elif scale_factor == '300GB':
            scale_factor = 'SFB (300GB)'
            sf = 'SFB'
        elif scale_factor == '1TB' or scale_factor == '10000000000':
            scale_factor = 'SF1 (1TB)'
            sf = 'SF1'
        elif scale_factor == '3TB' or scale_factor == '30000000000':
            scale_factor = 'SF3 (3TB)'
            sf = 'SF3'
        elif scale_factor == '10TB' or scale_factor == '100000000000':
            scale_factor = 'SF10 (10TB)'
            sf = 'SF10'
        elif scale_factor == '30TB' or scale_factor == '300000000000':
            scale_factor = 'SF30 (30TB)'
            sf = 'SF30'
        elif scale_factor == '100TB' or scale_factor == '1000000000000':
            scale_factor = 'SF100 (100TB)'
            sf = 'SF100'
        else:
            scale_factor = 'SF - not found'
            sf = 'SF-not Found'
        #print scale_factor
        #worksheet.write(27, 0, scale_factor, bold)

        if len(scale_factor) > 5:
            job_type = ['TeraGen', 'TeraSort', 'TeraValidate']
        else:
            job_type = ['HSGen', 'HSSort', 'HSValidate']

        #worksheet.write_row('B35', job_type, bold)
        
        return scale_factor, job_type

    def createReport(self, job_id, results_file, scale_factor):
        config = importlib.import_module('config_reports')
        cdh_config = importlib.import_module('config_cdh5')
        if cdh_config.tpc_flag == 'true':
            job = 'Gen'
        else:
            job = 'gen'
        tpc_flag = cdh_config.tpc_flag
        #job_id = config.job_id
        #results_file = config.results_file
        job_history_ip = config.job_history_ip # '172.16.14.97'
        
        node = config.node # = 'r3s1xd8.ignition.dell.'
        metric = 'CPU Total'
        #results_file = config.results_file
        if tpc_flag == 'true':
            file_1 = 'file_1.log'
            file_2 = 'file_2.log'
            tpc_log = ReportBuilder.copyTPCLog(scale_factor)
            sf_value, sf_result = ReportBuilder.getTPCResults(tpc_log, scale_factor)
            ReportBuilder.splitTPCReport(results_file)
            print sf_value
            if float(sf_value[0]) > float(sf_value[1]):
                print 'Results 1 is repeatablity run: ' + str(sf_value[0])
                print 'Results 2 is performance run: ' + str(sf_value[1])
                results_file = file_2
            else:
                print 'Results 1 is performance run: ' + str(sf_value[0])
                print 'Results 2 is repeatablity run: ' + str(sf_value[1])
                results_file = file_1
        else:
            sf_value = ['NA', 'NA']

        bob = ReportBuilder()
        
        if tpc_flag == 'true':
            row_2_sf = scale_factor
        else:
            row_2_sf = bob.convertRowToSF(bob.getSF(job, node, metric, results_file))

        workbook = xlsxwriter.Workbook('TPC_report ' + row_2_sf + ' ' + job_id + '.xlsx')
        worksheet = workbook.add_worksheet()
        
        headers = bob.getHeaders(results_file)
        #print headers
     
        bold = workbook.add_format({'bold': 1})
        left_format = workbook.add_format({'align': 'left'})
        
        worksheet.write(0, 0, headers, bold)
        
        #if tpc_flag == 'true':

        # add run_results from TPC file
        start_line = 36
        row = start_line
        for each in sf_value:
            #print each
            worksheet.write(row, 5, str(each))  
            row += 1

        #print job_id
        #node = config.node # = 'r3s1xd8.ignition.dell.'
        history_location = config.history_location #'hdfs:///user/history/done/2016/01/20/000000/'
        print 'H loc: ' + str(history_location)
        self.copyJobHistoryFiles(job_history_ip, history_location, job_id)
        
        params = config.params
        
        config_params = bob.getConfigParams(job_id, params)
        bob.writeConfigParams(config_params, worksheet)

        bob.writeMetrics(worksheet)
        #print results_file
        a, b, = bob.getResourceMetrics(worksheet, results_file)
        worksheet.write(27, 0, a, bold)
        worksheet.write_row('B35', b, bold)
        
        time_info, job_info, job_ids, containers = bob.getJobInformation(results_file)
        worksheet.write_row('B36', time_info)

        tsph = 0
        for each in time_info:
            tsph += float(each)
        tsph = 30*3600/tsph
        worksheet.write(35, 5, tsph, left_format)

        bob.writeJobLogInfo(job_ids, worksheet, containers)

        worksheet.set_column('A:A', 50)
        worksheet.set_column('B28:B38', 24)
        worksheet.set_column('C:F', 18)
        #worksheet.set_row(35,37, bold)
        # Make the header row larger.
        worksheet.set_row(0, 15, bold)
        # Make the headers bold.
        
        job_heads = ['Job Name', 'Job ID', 'Start Date', 'Start Time', 'Finish Date', 'Finish Time']
        worksheet.write_row('A29', job_heads, bold)
        
        start_line = 35
        run_info = ('TSph', 'Run 1', 'Run 2')
        for each in run_info:
            row = int(run_info.index(each) + start_line)
            worksheet.write(row, 4, str(each), bold)
        #write_columns(run_info, 35, 4)
          
        workbook.close()
        
    @staticmethod
    def splitTPCReport(results_log):
        #config = importlib.import_module('config_reports')
        #tpc_location_ip = config.tpc_location_ip
        #tpc_log = 'tpc_log.log' #config.tpc_log #'tpc_log.log'
        #textfile = open(tpc_log)
        file_1 = 'File_1.log'
        file_2 = 'File_2.log'
        results_log = open(results_log)
        header = results_log.readline()
        #print header
        a = open(file_1, 'w+')
        a.write(header + "\n")
        b = open(file_2, 'w+')
        b.write(header + "\n")
        second_file = False
        #target = file_1

        # write the contents from the results log into file_1 and file_2
        for line in results_log:
            #print line
            if second_file == False:
                a = open(file_1, 'a')
                a.write(line)# + "\n")
                a.close()
            else:
                b = open(file_2, 'a+')
                b.write(line)# + "\n")
                b.close()
            if '**********  end of run one   ***********' in line:
                second_file = True
                #target = file_2

        time.sleep(5)

    @staticmethod
    def copyTPCLog(scale_factor):  
        config = importlib.import_module('config_reports')
        tpc_location_ip = config.tpc_location_ip
        # copy the TPC log from it's remote location to the jumpbox so it can be split for the report builder.
        tpc_file_location = '/TPCx-HS_Tools/TPCx-HS_Kit_v1.3.0_external/TPCx-HS-Runtime-Suite/'
        #scale_factor = '100GB'
        remote_file = tpc_file_location + 'TPCx-HS-result-' + scale_factor + '.log'
        local_file = 'TPCx-HS-result-' + str(scale_factor) + '.log'
        print 'finding: ' + remote_file
        Scp.get_file(tpc_location_ip, 'root', 'Ignition01', local_file, remote_file)


        tpc_log = local_file
        
        return tpc_log

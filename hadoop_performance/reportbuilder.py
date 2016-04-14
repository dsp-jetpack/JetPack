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
        print line1
        ma = re.search("\[\[\[(.+)\]\]\]", line1)
        if ma:
            headers = ma.group(1)
            
        return headers
        
    def copyJobHistoryFiles(self, job_history_ip, history_location, job_id):
        cmd = 'sudo -u hdfs hadoop fs -get '+history_location+'' + job_id + '_conf.xml /tmp/'+job_id
        print cmd
        cmd1 = 'mkdir /tmp/'+job_id
        cmd2 = 'chmod 777 /tmp/'+job_id
        out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd1)
        print cmd1
        out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd2)
        print cmd2
        out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd)
        print cmd
        
        remotefile = '/tmp/'+job_id+'/'+job_id+'_conf.xml'
        print remotefile
        localfile = job_id+'_conf.xml'
        print localfile
        
        Scp.get_file(job_history_ip, 'root', 'Ignition01', localfile, remotefile)
        print out
        print err
        
       

    def getConfigParams(self, job_id, params):
        config_params = []
        my_file = job_id+'_conf.xml'
        print my_file
        
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

    def writeJobLogInfo(self, job_ids, worksheet):
    
        job_file = open('jobLog.log')
        #row, col = 0
        #rows = ['B30', 'B31', 'B32']
        row = 29
        print job_file
        print job_ids
        for line in job_file:
            #print line
            for job in job_ids:
                #print 'job: ' + str(job)
                if job in line:
                    #print line
                    row_data = line.split(' ')
                    print row_data
                    for each in row_data:
                        print each
                        if row_data.index(each) == 0:
                            row_data[0] = each + ' ' + str('(max containers = )')
                            print each
                    print row_data
                    worksheet.write_row(row, 0, row_data)
                    row += 1

    def getTPCResults(self, textfile, worksheet):
        run_results = []
        for line in textfile:
            if 'Performance Metric' in line:
                ma = re.search(": (.+) ", line)
                if ma:
                    sf_result = ma.group(1)
                    if sf_result == 'NA':
                        run_results.append(str(sf_result))
                    else:
                        run_results.append(str(sf_result) + '@' + sf)
        print run_results
        start_line = 36
        row = start_line
        for each in run_results:
            print each
            #row = int(run_results.index(each) + start_line)
            #row += start_line
            worksheet.write(row, 5, str(each))
            row += 1
        #write_columns(run_results, 36, 5)
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
    
    
    def createWorkbook(self, row_2_sf, job_id, workbook, worksheet):
        config = importlib.import_module('config_reports')
        print 'creating workbook'
        #workbook = xlsxwriter.Workbook('TPC_report ' + row_2_sf + ' ' + job_id + '.xlsx')
        # Add a worksheet
        #worksheet = workbook.add_worksheet()
        
        # Add a bold format for the headers.
        bold = workbook.add_format({'bold': 1})
        left_format = workbook.add_format({'align': 'left'})
        
        # Make the headers bold.
        #headers = ''
        
        #worksheet.write(0, 0, headers, bold)
        
        #results_file = config.results_file

        
        # headers = self.getHeaders(results_file)
        # print headers
 
        # bold = workbook.add_format({'bold': 1})
    
        # worksheet.write(0, 0, headers, bold)
    
        config_params = []
        job_history_ip = config.job_history_ip
        
        
        print job_id
        node = config.node # = 'r3s1xd8.ignition.dell.'
        history_location = config.history_location #'hdfs:///user/history/done/2016/01/20/000000/'
        print 'H loc: ' + str(history_location)
        self.copyJobHistoryFiles(job_history_ip, history_location, job_id)
        
        # cmd = 'sudo -u hdfs hadoop fs -get '+history_location+'' + job_id + '_conf.xml /tmp/'+job_id
        # cmd1 = 'mkdir /tmp/'+job_id
        # cmd2 = 'chmod 777 /tmp/'+job_id
        # out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd1)
        # print cmd1
        # out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd2)
        # print cmd2
        # out, err = Ssh.execute_command(job_history_ip, 'root', 'Ignition01', cmd)
        # print cmd
        
        # remotefile = '/tmp/'+job_id+'/'+job_id+'_conf.xml'
        # print remotefile
        # localfile = job_id+'_conf.xml'
        # print localfile
        
        # Scp.get_file(job_history_ip, 'root', 'Ignition01', localfile, remotefile)
        # print out
        # print err
        params = config.params
        config_params = self.getConfigParams(job_id, params)
        
        # my_file = job_id+'_conf.xml'
        # print my_file
        
        # textfile = open(my_file)
        # params = config.params
        # for line in textfile:
            # for p in params:
                # if '<name>'+p+'</name>' in line:
                    # #print line
                    # ma = re.search("value>(.+)</value", line)
                    # if ma:
                        # param = ma.group(1)
                        # #print param
                        # config_params.append(dict({p:param}))
                        
        self.writeConfigParams(config_params, worksheet)
        # row = 1
        # for each in config_params:
            # #print each.keys()[0]
            # #print each.values()[0]
            # worksheet.write(row, 0, str(each.keys()[0]))
            # worksheet.write(row, 1, str(each.values()[0]))
            # row += 1


        job_heads = ['Job Name', 'Job ID', 'Start Date', 'Start Time', 'Finish Date', 'Finish Time']
        
        time_info, job_info, job_ids = self.getJobInformation(results_file)
        print time_info
        worksheet.write_row('B36', time_info)
        tsph = 0
        for each in time_info:
            tsph += float(each)
        tsph = 30*3600/tsph
        worksheet.write(35, 5, tsph, left_format)
        
        # textfile = open(results_file)
        # for line in textfile:
            # #print line
            # if 'JobID' in line and 'gen' in line:
                # #print line
                # # Split the input data based on whitespace.
                # ma = re.search("JobID: (.+)", line)
                # if ma:
                    # job_id = ma.group(1) 
                # job = 'Gen ' + str(job_id)
                # #print job
                # #print job_id
                # job_info.append(job)
                # job_ids.append(job_id)

            # if 'JobID' in line and 'sort' in line:
                # # Split the input data based on whitespace.
                # ma = re.search("JobID: (.+)", line)
                # if ma:
                    # job_id = ma.group(1) 
                # job = 'sort ' + str(job_id)
                # job_info.append(job)
                # job_ids.append(job_id)

            # if 'JobID' in line and 'validate' in line:
                # # Split the input data based on whitespace.
                # ma = re.search("JobID: (.+)", line)
                # if ma:
                    # job_id = ma.group(1) 
                # job = 'validate ' + str(job_id)
                # job_info.append(job)
                # job_ids.append(job_id)
                # #for each in row_data:
                # #    print each
                # #print row_data[-1]
                # #worksheet.write_row('A19', row_data[-1])
            # if 'runtime' in line and 'Gen' in line:
                # line = line.split(' | ')
                # runtime = line[-1]
                # ma = re.search("\((.+) seconds", runtime)
                # if ma:
                    # runtime = ma.group(1)
                    # print runtime
                # time_info.append(runtime)
            # if 'runtime' in line and 'Sort' in line:
                # line = line.split(' | ')
                # runtime = line[-1]
                # ma = re.search("\((.+) seconds", runtime)
                # if ma:
                    # runtime = ma.group(1)
                    # print runtime
                # time_info.append(runtime)
            # if 'runtime' in line and 'Validate' in line:
                # line = line.split(' | ')
                # runtime = line[-1]
                # ma = re.search("\((.+) seconds", runtime)
                # if ma:
                    # runtime = ma.group(1)
                    # print runtime
                # time_info.append(runtime)

        # print time_info
        worksheet.write_row('B36', time_info)
        tsph = 0
        for each in time_info:
            tsph += float(each)
        tsph = 30*3600/tsph
        worksheet.write(35, 5, tsph, left_format)
        
        job_file = open('jobLog.log')
        #row, col = 0
        #rows = ['B30', 'B31', 'B32']
        row = 29
        print job_file
        print job_ids
        for line in job_file:
            #print line
            for job in job_ids:
                #print 'job: ' + str(job)
                if job in line:
                    #print line
                    row_data = line.split(' ')
                    print row_data
                    for each in row_data:
                        print each
                        if row_data.index(each) == 0:
                            row_data[0] = each + ' ' + str('(max containers = )')
                            print each
                    print row_data
                    worksheet.write_row(row, 0, row_data)
                    row += 1

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
                    
        # #jobs = ('TPC-HSGen', 'TPC-HSSort', 'TPC-HSValidate')
        # jobs = ('gen', 'sort', 'validate')
        # metrics = ('CPU Total', 'bytes_in', 'bytes_out', 'physical_memory_used', 'total_read_bytes_rate_across_disks', 'total_write_bytes_rate_across_disks')

        # row = 36
        # for metric in metrics:
            # col = 1
            # for job in jobs:
                # bytes = ['bytes', 'KBs', 'MBs', 'GBs', 'TBs']
                # size = 0
                # value = float(bob.getMetric(job, node, metric)[0])
                # if metric != 'CPU Total':
                    # while float(value) > 1024:
                        # value = value/1024
                        # size += 1
                        # #print value
                    # #print bytes[size]
                    # value = round(value, 2)
                    # value = str(value) + ' ' + str(bytes[size])
                # else:
                    # value = round(value, 2)
                    # value = str(value) + ' %'
                # worksheet.write(row, col, str(value))
                # col += 1
            # row += 1

        # scale_factor = bob.getSF(job, node, metric)

        # if scale_factor == '100GB':
            # scale_factor = 'SFA (100GB)'
            # sf = 'SFA'
        # elif scale_factor == '300GB':
            # scale_factor = 'SFB (300GB)'
            # sf = 'SFB'
        # elif scale_factor == '1TB' or scale_factor == '10000000000':
            # scale_factor = 'SF1 (1TB)'
            # sf = 'SF1'
        # elif scale_factor == '3TB' or scale_factor == '30000000000':
            # scale_factor = 'SF3 (3TB)'
            # sf = 'SF3'
        # elif scale_factor == '10TB' or scale_factor == '100000000000':
            # scale_factor = 'SF10 (10TB)'
            # sf = 'SF10'
        # elif scale_factor == '30TB' or scale_factor == '300000000000':
            # scale_factor = 'SF30 (30TB)'
            # sf = 'SF30'
        # elif scale_factor == '100TB' or scale_factor == '1000000000000':
            # scale_factor = 'SF100 (100TB)'
            # sf = 'SF100'
        # else:
            # scale_factor = 'SF - not found'
            # sf = 'SF-not Found'
        # print scale_factor
        # worksheet.write(27, 0, scale_factor, bold)
        
        

        
        # if len(scale_factor) > 5:
            # job_type = ['TeraGen', 'TeraSort', 'TeraValidate']
        # else:
            # job_type = ['HSGen', 'HSSort', 'HSValidate']

        # worksheet.write_row('B35', job_type, bold)
        
        tpc_log = config.tpc_log #'tpc_log.log'
        textfile = open(tpc_log)

        start_line = 35
        run_info = ('TSph', 'Run 1', 'Run 2')
        for each in run_info:
            row = int(run_info.index(each) + start_line)
            worksheet.write(row, 4, str(each), bold)
        #write_columns(run_info, 35, 4)
        
        run_results = []
        for line in textfile:
            if 'Performance Metric' in line:
                ma = re.search(": (.+) ", line)
                if ma:
                    sf_result = ma.group(1)
                    if sf_result == 'NA':
                        run_results.append(str(sf_result))
                    else:
                        run_results.append(str(sf_result) + '@' + sf)
        print run_results
        start_line = 36
        row = start_line
        for each in run_results:
            print each
            #row = int(run_results.index(each) + start_line)
            #row += start_line
            worksheet.write(row, 5, str(each))
            row += 1
        #write_columns(run_results, 36, 5)

        worksheet.set_column('A:A', 50)
        worksheet.set_column('B28:B38', 24)
        worksheet.set_column('C:F', 18)
        #worksheet.set_row(35,37, bold)
        # Make the header row larger.
        worksheet.set_row(0, 15, bold)
        # Make the headers bold.
        worksheet.write_row('A29', job_heads, bold)

        workbook.close()
        return workbook, worksheet

    def getJobInformation(self, results_file):
    
        time_info = []
        job_info = []
        job_ids = []

        textfile = open(results_file)
        for line in textfile:
            #print line
            if 'JobID' in line and 'gen' in line:
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

            if 'JobID' in line and 'sort' in line:
                # Split the input data based on whitespace.
                ma = re.search("JobID: (.+)", line)
                if ma:
                    job_id = ma.group(1) 
                job = 'sort ' + str(job_id)
                job_info.append(job)
                job_ids.append(job_id)

            if 'JobID' in line and 'validate' in line:
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
            if 'runtime' in line and 'Gen' in line:
                line = line.split(' | ')
                runtime = line[-1]
                ma = re.search("\((.+) seconds", runtime)
                if ma:
                    runtime = ma.group(1)
                    print runtime
                time_info.append(runtime)
            if 'runtime' in line and 'Sort' in line:
                line = line.split(' | ')
                runtime = line[-1]
                ma = re.search("\((.+) seconds", runtime)
                if ma:
                    runtime = ma.group(1)
                    print runtime
                time_info.append(runtime)
            if 'runtime' in line and 'Validate' in line:
                line = line.split(' | ')
                runtime = line[-1]
                ma = re.search("\((.+) seconds", runtime)
                if ma:
                    runtime = ma.group(1)
                    print runtime
                time_info.append(runtime)

        #print time_info
        #worksheet.write_row('B36', time_info)
        #tsph = 0
        #for each in time_info:
        #    tsph += float(each)
        #tsph = 30*3600/tsph
        #worksheet.write(35, 5, tsph, left_format)
        
        return time_info, job_info, job_ids


    def getMetric(self, job, node, metric, results_file):
        config = importlib.import_module('config_reports')
        # results_file = config.results_file # 'SF1-3 resultsB.txt'
        value = []
        textfile = open(results_file)
        for line in textfile:
            if job in line and node in line and metric in line:
                # Split the input data based on 'bar'.
                row_data = line.split(' | ')
                #for each in row_data:
                #    print each
                    #value.append(each)
                print row_data[-1]
                value.append(row_data[-1])
            
        return value

    def getSF(self, job, node, metric, results_file):
        config = importlib.import_module('config_reports')
        #results_file = config.results_file # 'SF1-3 resultsB.txt'
        location = config.report_location
        value = []
        #results_file = '/'+ location + '/' + results_file
        print results_file
        textfile = open(results_file)
        for line in textfile:
            if job in line and node in line and metric in line:
                # Split the input data based on 'bar'.
                row_data = line.split(' | ')
                print row_data[2]
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
        node = 'r3s1xd8.ignition.dell.'
        #jobs = ('TPC-HSGen', 'TPC-HSSort', 'TPC-HSValidate')
        jobs = ('gen', 'sort', 'validate')
        metrics = ('CPU Total', 'bytes_in', 'bytes_out', 'physical_memory_used', 'total_read_bytes_rate_across_disks', 'total_write_bytes_rate_across_disks')

        row = 36
        for metric in metrics:
            col = 1
            for job in jobs:
                bytes = ['bytes', 'KBs', 'MBs', 'GBs', 'TBs']
                size = 0
                value = float(self.getMetric(job, node, metric, results_file)[0])
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
        print scale_factor
        #worksheet.write(27, 0, scale_factor, bold)

        if len(scale_factor) > 5:
            job_type = ['TeraGen', 'TeraSort', 'TeraValidate']
        else:
            job_type = ['HSGen', 'HSSort', 'HSValidate']

        #worksheet.write_row('B35', job_type, bold)
        
        return scale_factor, job_type

    def createReport(self, job_id, results_file):
        config = importlib.import_module('config_reports')
        job = 'gen'
        #job_id = config.job_id
        #results_file = config.results_file
        job_history_ip = config.job_history_ip # '172.16.14.97'
        
        node = config.node # = 'r3s1xd8.ignition.dell.'
        metric = 'CPU Total'
        #results_file = config.results_file
        
        bob = ReportBuilder()
        
        row_2_sf = bob.convertRowToSF(bob.getSF(job, node, metric, results_file))
        workbook = xlsxwriter.Workbook('TPC_report ' + row_2_sf + ' ' + job_id + '.xlsx')
        worksheet = workbook.add_worksheet()
        
        headers = bob.getHeaders(results_file)
        print headers
     
        bold = workbook.add_format({'bold': 1})
        left_format = workbook.add_format({'align': 'left'})
        
        worksheet.write(0, 0, headers, bold)
        
        print job_id
        #node = config.node # = 'r3s1xd8.ignition.dell.'
        history_location = config.history_location #'hdfs:///user/history/done/2016/01/20/000000/'
        print 'H loc: ' + str(history_location)
        self.copyJobHistoryFiles(job_history_ip, history_location, job_id)
        
        params = config.params
        
        config_params = bob.getConfigParams(job_id, params)
        bob.writeConfigParams(config_params, worksheet)

        bob.writeMetrics(worksheet)
        a, b, = bob.getResourceMetrics(worksheet, results_file)
        worksheet.write(27, 0, a, bold)
        worksheet.write_row('B35', b, bold)
        
        time_info, job_info, job_ids = bob.getJobInformation(results_file)
        worksheet.write_row('B36', time_info)

        tsph = 0
        for each in time_info:
            tsph += float(each)
        tsph = 30*3600/tsph
        worksheet.write(35, 5, tsph, left_format)

        bob.writeJobLogInfo(job_ids, worksheet)

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
        
        tpc_log = config.tpc_log #'tpc_log.log'
        textfile = open(tpc_log)
        bob.getTPCResults(textfile, worksheet)
        
        workbook.close()
    
#def main():
    #ReportBuilder.createReport()
    # bob = ReportBuilder()
    
    # config = importlib.import_module('config_reports')
    # job = 'gen'
    # job_id = config.job_id
    # node = config.node # = 'r3s1xd8.ignition.dell.'
    # metric = 'CPU Total'
    # results_file = config.results_file
    
    # row_2_sf = bob.convertRowToSF(bob.getSF(job, node, metric))
    
    # workbook = xlsxwriter.Workbook('TPC_report ' + row_2_sf + ' ' + job_id + '.xlsx')
    # worksheet = workbook.add_worksheet()
    

    # #my_workbook, my_worksheet = bob.createWorkbook(row_2_sf, job_id, workbook, worksheet)
    
    # headers = bob.getHeaders(results_file)
    # print headers
 
    # bold = workbook.add_format({'bold': 1})
    # left_format = workbook.add_format({'align': 'left'})
    
    # worksheet.write(0, 0, headers, bold)
    
    # params = config.params

    # config_params = bob.getConfigParams(job_id, params)
    # bob.writeConfigParams(config_params, worksheet)

    # bob.writeMetrics(worksheet)
    # a, b, = bob.getResourceMetrics(worksheet)
    # worksheet.write(27, 0, a, bold)
    # worksheet.write_row('B35', b, bold)
    
    # time_info, job_info, job_ids = bob.getJobInformation(results_file)
    # worksheet.write_row('B36', time_info)

    # tsph = 0
    # for each in time_info:
        # tsph += float(each)
    # tsph = 30*3600/tsph
    # worksheet.write(35, 5, tsph, left_format)

    # bob.writeJobLogInfo(job_ids, worksheet)

    # worksheet.set_column('A:A', 50)
    # worksheet.set_column('B28:B38', 24)
    # worksheet.set_column('C:F', 18)
    # #worksheet.set_row(35,37, bold)
    # # Make the header row larger.
    # worksheet.set_row(0, 15, bold)
    # # Make the headers bold.
    
    # job_heads = ['Job Name', 'Job ID', 'Start Date', 'Start Time', 'Finish Date', 'Finish Time']
    # worksheet.write_row('A29', job_heads, bold)
    
    # start_line = 35
    # run_info = ('TSph', 'Run 1', 'Run 2')
    # for each in run_info:
        # row = int(run_info.index(each) + start_line)
        # worksheet.write(row, 4, str(each), bold)
    # #write_columns(run_info, 35, 4)
    
    # tpc_log = config.tpc_log #'tpc_log.log'
    # textfile = open(tpc_log)
    # bob.getTPCResults(textfile, worksheet)
    
    # workbook.close()

#if __name__ == '__main__':
#    main()
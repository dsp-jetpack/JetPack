<?php 
/*
 * OpenStack - A set of software tools for building and managing cloud computing
 * platforms for public and private clouds.
 * Copyright (C) 2015 Dell, Inc.
 *
 * This file is part of OpenStack.
 *
 * OpenStack is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * OpenStack is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with OpenStack.  If not, see <http://www.gnu.org/licenses/>.
 */ ?>
<?php

$version_a = $_GET['version'];
$stat = $_GET['stat'];
$type = $_GET['type'];
$averageOnly = $_GET['average'];

ini_set('max_execution_time', 14000);


$con=mysqli_connect("localhost","root","","hadoop_performance");



$testDataRange = array();
$result = mysqli_query($con,"SELECT distinct(test_data) FROM results where run_id = '". $version_a . "' and test_type ='".$type."'");
while($row = mysqli_fetch_array($result)){
	array_push($testDataRange, $row['test_data']);
	//echo $row['test_data'] ."<br>";
}
// Create column for x
$table = '{ "cols":[';
$table = $table . '{"id":"", "label":"test_data","pattern":"", "type":"string"},';
// Hosts lists 
$result = mysqli_query($con,"select distinct(result_type) FROM hadoop_performance.results where run_id='". $version_a . "' and test_type = '".$type."' and result_identifier = '". $stat ."'  order by result_type desc");

$hosts = array();
while($row = mysqli_fetch_array($result)){
	
	if ($averageOnly == "false") {	
		$table = $table . '{"id":"", "label":"'.$row['result_type'].'","pattern":"", "type":"number"},';
	}
	else {
		if ($row['result_type'] == "average") {
			//echo "<br> adding avg $oo<br>";
			$table = $table . '{"id":"", "label":"datanodes average","pattern":"", "type":"number"},';
		}
		elseif (  $row['result_type']=="job") {
			//echo "<br> adding Job $oo<br>";
			$table = $table . '{"id":"", "label":"job duration","pattern":"", "type":"number"},';
		}
		
	}
}
$table = rtrim($table, " ,");
$table = $table . '], "rows": [';

foreach ($testDataRange as $dataPoint) {
	
	$query = mysqli_query($con,"select test_data, result_type, result_datapoint, result_identifier FROM hadoop_performance.results where run_id='". $version_a ."' and test_type = '".$type."' and result_identifier = '".$stat . "' and test_data='". $dataPoint ."' order by result_type desc");

	$table = $table . '{"c":[{"v":"'.$dataPoint.'","f":null},';
	while($row = mysqli_fetch_array($query)){
		// 
		$resType = $row['result_type'];
		if ($averageOnly == "true") {
			if ($resType == "job" || $resType == "average") {
				$table = $table .  '{"v":'.$row['result_datapoint'].',"f":null},';
			}
		}
		else{
			$table = $table .  '{"v":'.$row['result_datapoint'].',"f":null},';
		}
		
	}
	$table = rtrim($table, " ,");
	$table = $table . ']},'	;
}
$table = rtrim($table, " ,");
$table = $table . ']}';
echo  $table ;







		
?>
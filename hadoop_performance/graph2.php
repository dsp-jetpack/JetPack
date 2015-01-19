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
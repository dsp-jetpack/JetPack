<?php

print_r($_FILES);

$file = $_FILES['file'];

echo "received $file <br>";

$fileContent = file($file['tmp_name']);



$mysqli = new mysqli('10.21.255.226', 'tempest', 'T3mp3sT!', 'hadoop_performance');
if (mysqli_connect_errno()) {
	printf("Connect failed: %s\n", mysqli_connect_error());
	exit();
}
else{
	printf("Errormessage: %s\n", $mysqli->error);
}


foreach ($fileContent as $each){
	$fields = explode("|", $each);
	if ( $stmt = $mysqli->prepare("INSERT INTO results VALUES (?, ?, ?, ?, ?, ?)") ) {
		$stmt->bind_param("ssssss", $fields[1], $fields[2], $fields[3], $fields[4], $fields[5], $fields[6]);
		$stmt->execute();
		$stmt->close();
	}
}


$mysqli->close();
echo "results uploaded";

?>


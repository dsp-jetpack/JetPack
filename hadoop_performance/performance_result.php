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
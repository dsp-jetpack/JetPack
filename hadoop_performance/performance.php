<?php
header("Access-Control-Allow-Origin: *");



?>
<head>
<link rel="shortcut icon" href="/graph.jpeg"> 


    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript" src="//ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js"></script>
    <script type="text/javascript">
    
    // Load the Visualization API and the piechart package.
    google.load('visualization', '1', {'packages':['corechart']});
      
    // Set a callback to run when the Google Visualization API is loaded.
    //google.setOnLoadCallback(drawChart);
      
    </script>


<script>
function getValue(element){
  var x=document.getElementById(element);
  for (var i = 0; i < x.options.length; i++) {
     if(x.options[i].selected ==true){
          return x.options[i].text;
      }
  }
}
</script>
<script type="text/javascript" src="//www.google.com/jsapi"></script>

<script>
function get_results(){
	var a=getValue('version_a');
	if (a == ".."){
		return;
	}
	//get the stats available & load them up v
	terragen_stats = JSON.parse(get_available_stats(a, 'terragen'));
	dfsio_stats = JSON.parse(get_available_stats(a, 'dfsio'));
	
	for (var i=0;i<terragen_stats.length;i++){ 
		console.log("loading terragen into container " + i);
		load_stat(terragen_stats[i], 'results'+i, 'terragen');
	}
	for (var p=i;p<dfsio_stats.length;p++){
		console.log("loading dfsio into container " + p);
		load_stat(dfsio_stats[p], 'results'+p, 'dfsio');
	}

}



function load_stat(stat, container, type){
	var a=getValue('version_a');	
	var averagesOnly = document.getElementById('average').checked;
	//alert(averagesOnly);
	document.getElementById(container).innerHTML="<img src=\"throbber.gif\" alt=\"Smiley face\">";
	var xmlhttp=new XMLHttpRequest();
	xmlhttp.onreadystatechange=function(){	
		if (xmlhttp.readyState==4 && xmlhttp.status==200){
			var data = new google.visualization.DataTable(xmlhttp.responseText);
			var chart = new google.visualization.ComboChart(document.getElementById(container));
			var j = JSON.parse(xmlhttp.responseText)
			var len = (j.cols.length) -2 ;
			var ll = parseInt(len);
			if (ll == -1){
				document.getElementById(container).innerHTML=" ";
				return "nope";
			}
			else if (ll <= 0 ) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	series: {0:{type: "line", curveType: "function"}}
			  		});   	
			}
			else if (ll ==1){
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {2:{type: "area"}}
			  		});   
			}  
			else if (ll ==2) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {2:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==3) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {3:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==4) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {4:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==5) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {5:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==6) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {6:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==7) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {7:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==8) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {8:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==9) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {9:{type: "area"}}
			  		});	  
	  		}
			else if (ll ==10) {
				chart.draw(data, {
			    	title : stat,
			    	width: 600,
			    	height: 400,
			    	hAxis: {title: type + "test data count"},
			    	vAxis: {title: "result"},
			    	seriesType: "bars",
			  		curveType: "function",
			  		series: {10:{type: "area"}}
			  		});	  
				}
			else{
				alert('wtf? ' + stat + ' : ' + ll);
	  		}
			
	  		}
	}
	xmlhttp.open("GET","graphs2.php?version="+a+"&stat="+stat+"&type="+type+"&average="+averagesOnly, true);
	xmlhttp.send();
}

function get_available_stats(version, test_type){
	var a=getValue('version_a');	
	

	for (var i=0;i<50;i++){ 
		document.getElementById('results'+i).innerHTML=""
	}
	document.getElementById('results0').innerHTML="<img src=\"throbber.gif\" alt=\"Smiley face\">";
	
	var xmlHttp = null;
    xmlHttp = new XMLHttpRequest();
    
	if (test_type == 'dfsio'){
		xmlHttp.open("GET","get_dfsio_stats.php?version="+a, false);
	}
	else if(test_type =='terragen'){
		xmlHttp.open("GET","get_terragen_stats.php?version="+a, false);
	}
    xmlHttp.send( null );
    console.log(xmlHttp.responseText);
    return xmlHttp.responseText;

	
	xmlhttp.send();
}

</script>

</head>
<body>
<?php

$con=mysqli_connect("localhost","root","","hadoop_performance");
$result = mysqli_query($con,"SELECT distinct(run_id) FROM results");
$version = array("..");
while($row = mysqli_fetch_array($result)){
  $val = $row['run_id'];
  array_push($version, $val );
  }
mysqli_close($con);


echo "<form id=\"bla\">";
echo "<select id='version_a' onchange=\"get_results()\">";
foreach($version as $each){
	echo"<option>$each</option>";
}
echo "</select>";
echo '<input type="checkbox" id="average" onchange="get_results()"> show average only<br>';
echo "</form>";

			
echo "<img  name='refresh' src=\"refresh_icon.jpg\" alt=\"refresh\" height=\"20\" width=\"20\" onclick=\"get_results()\">";
echo '<left></left>';

echo "<table id='teragen_charts'>";

for ($i = 0; $i < 50; $i++){
	echo "<tr>";
	
	echo "<td><div id=\"results".$i."\"> </div></td>";
	$i++;
	echo "<td><div id=\"results".$i."\"> </div></td>";
	echo "</tr>";

}


echo "</table>";


echo "</body>";
 
  
?>

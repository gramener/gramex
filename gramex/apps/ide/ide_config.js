/* eslint-env browser, jquery */
/* eslint-disable no-console, no-unused-vars, no-quotes, no-semi, no-indent */

$(function () {
  var config_url = "./changeConfig";     // url for editing config
  var config_tree = "#jstree";            // treeID in html
  var config_table = "#disp_table";       // tableID in html
  var config_table_body = "#table_body";  // tbodyID in html
  var yaml_file= "gramex.yaml";           // yaml file to be edited
  var config_data=[];          // populated by get call

  //GET data from table request and send
function get_node_data(){
  var row = 1;
  var prev_node_data = "{"
  $("table > tbody > tr").each(function () {
    //create object and json for the de-selected node here so that it can be updated
    var value = $(this).find('td').eq(1).text();
    value = value === 'true' ? true : value === 'false' ? false :
            (isNaN(value) ? '"'+value+'"' : value);
    prev_node_data = prev_node_data +' "'+row+'"'+
        ': {"key": "'+$(this).find('td').eq(0).text() +
        '", "value": '+value+
    '},'
    row = row+1;
  });
  // remove last comma
  var lastChar = prev_node_data.slice(-1);
  if (lastChar == ',') {
    prev_node_data = prev_node_data.slice(0, -1);
  }
  prev_node_data = prev_node_data + "}"
  return prev_node_data;
}

function append_table_row(k=null,v=null){
  var key, value;
  if(k){key = k}else{key = "Key"}
  if(v){value = v}else{value = "Value"}
  const row = `
  <tr class="hide">
  <td contenteditable="true"><strong>`+key+`</strong></td>
  <td contenteditable="true">`+value+`</td>
  <td><span class="table-up"><a href="#!" class="indigo-text"><i class="fas fa-long-arrow-alt-up" aria-hidden="true"></i></a></span>
    <span class="table-down"><a href="#!" class="indigo-text"><i class="fas fa-long-arrow-alt-down" aria-hidden="true"></i></a></span></td>
  <td><span class="table-duplicate"><button type="button" class="btn btn-info btn-rounded btn-sm my-0 waves-effect waves-light">Clone</button></span></td>
  <td><span class="table-remove"><button type="button" class="btn btn-danger btn-rounded btn-sm my-0 waves-effect waves-light">Remove</button></span></td>
  </tr>`;

  return row;
}
//Create an GET request and send
$.ajax({
  url: config_url+"?filename="+yaml_file,
  type: "get",
  data: {},
  dataType: 'json',
  success: function(response) {
  // create an config tree instance when the DOM is ready and data is received
    config_data = response;
    $(config_tree).jstree({
      "core" : {
      "animation" : 0,
      "multiple" : false,
      "check_callback" : true,
      "themes" : { "stripes" : true },
      "data" :  eval(config_data)
      },
      "plugins" : [
        "changed", "contextmenu", "dnd", "search", "state", "types", "wholerow"
      ]
    });
  },
  error: function(xhr) {
  console.log("Error while getting config data");//Do Something
  }
});

// bind to events triggered on the tree
$(config_tree)
.on("changed.jstree", function (e, data) {

  // save/update data for previous node if modified
  var prev_node = $(config_tree).jstree(true).get_node(data.changed.deselected[0]);

  if (typeof prev_node !== 'úndefined'){
    prev_node.data = JSON.parse(get_node_data());
  }

  var selectedNode = $(config_tree).jstree('get_selected',true)[0];
  if (typeof selectedNode !== "undefined") {
    if (selectedNode.data !== null){
      var i, no_keys = Object.keys(selectedNode.data).length;
      var current_table = document.getElementById(config_table);

      // First clear the table data and then insert from selected node
      $(config_table_body).empty();
      for (i=1 ; i <= no_keys; i++){
        $(config_table_body).append(append_table_row(selectedNode.data[i].key,selectedNode.data[i].value));
        $('i').prop('disabled', false).css('opacity',1);
      }
      if (selectedNode.parent === selectedNode.text){
          $('.table-duplicate').prop('disabled', true).css('opacity',0.5);
          $('i').prop('disabled', true).css('opacity',0.5);
          $('.table-remove').prop('disabled', true).css('opacity',0.5);
      }
    }
    else{
      $(config_table_body).empty();
    }
  }
});
$(config_tree)
.on("copy_node.jstree", function (e, data) {
  data.node.data = $.extend(true, {}, data.original.data);
  if (data.node.children_d.length > 0) {
    var tree = $(this).jstree(true);
    for (var i = 0; i < data.node.children_d.length; i++) {
      var originalChild = tree.get_node(data.original.children_d[i]);
      var copiedChild = tree.get_node(data.node.children_d[i]);
      copiedChild.data = $.extend(true, {}, originalChild.data);
    }
  }
});

// Save data back
$('button').on('click', function () {
  // first update the changed data for current node, if any
  $(config_tree).jstree().get_selected(true)[0]['data'] = JSON.parse(get_node_data());

  // set flat:true to get all nodes in 1-level json
  var treeData = $(config_tree).jstree(true).get_json('#', {flat:true})
  var jsonData = treeData.map(({id, parent, text, data}) => ({id, parent, text, data}));
  var xdata = JSON.stringify(jsonData);
  //Create an POST request and send
  $.ajax({
    url: config_url+"?filename="+yaml_file,
    type: "post",
    data: xdata,
    dataType: 'json',
    success: function(response) {
      console.log("POST Successful");
    },
    error: function(xhr) {
    console.log("Error while posting config data");
    }
  });
});
// Insert new node into the key/value table
$('.table-add').on('click', 'i', () => {
  $('tbody').append(append_table_row());
});
// Append duplicated row at the end of the table
$(config_table).on('click', '.table-duplicate', function () {
  const $row = $(this).parents('tr').clone();
  $('tbody').append($row);
});
// Delete current row from the table
$(config_table).on('click', '.table-remove', function () {
  $(this).parents('tr').detach();
});
// Swap with the previous row
$(config_table).on('click', '.table-up', function () {
  const $row = $(this).parents('tr');

  if ($row.index() === 0) {
    return;
  }
  $row.prev().before($row.get(0));
});
// Swap with the next row
$(config_table).on('click', '.table-down', function () {
  const $row = $(this).parents('tr');
  $row.next().after($row.get(0));
});

});

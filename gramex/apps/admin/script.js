/* global $, config, active_users, setTimeout */

function alertMessage(msgOne, context, timer) {
  var $msg = $('<div class="alert align-middle alert-' + context + ' alert-dismissable" role="alert">' +
    '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
    '<p class="message"> ' + msgOne + '</p></div>').appendTo('.page-alert')
  setTimeout(function () { $msg.slideUp(500, function () { $msg.alert('close') }) }, timer)
}

var src = 'users/'
var columns = [
  {
    name: '*'
  },
  {
    name: config.id,
    format: function (arg) {
      var isOnline = arg.row[config.id] in active_users ? '#35AC19' : '#ccc'
      var svg = '<svg height="20" width="20"><circle r="5" cx="10" cy="15" stroke-width="3" fill="' + isOnline + '"></circle></svg>'
      return svg + arg.row[config.id]
    },
    editable: true
  }
]

config.hide.map(function (col_name) {
  columns.push({
    name: col_name,
    hide: true
  })
})

columns.push({
  name: 'Actions',
  template: function () {
    return '<td>\
    <i class="fa fa-power-off fa-lg mr-2 cursor-pointer" title="logout user" data-action="logout"></i>\
    <a href="#">\
      <img src="reset_password.svg" width="25" title="reset password" data-action="reset_password" />\
    </a>\
    <i class="fa fa-trash fa-lg ml-2 cursor-pointer" title = "delete user" data-action="delete" ></i>\
    </td>'
  }
})

$('.formhandler').formhandler({
  src: src,
  columns: columns,
  count: false,
  page: false,
  size: false,
  exportFormats: {
    xlsx: 'Excel'
  },
  edit: true,
  add: true,
  actions: {
    'logout': function (row) {
      $.ajax('./pop_user', {
        method: 'GET',
        data: {
          user: row[config.id]
        },
        error: function () {
          alertMessage('Logout user failed!', 'warning', 2000)
        },
        success: function () {
          alertMessage(row[config.id] +' is logged out from all his sessions successfully!', 'info', 2000)
        }
      })
    },
    'delete': function (row, rowNo) {
      $('.loader').removeClass('d-none')
      $.ajax(src, {
        method: 'DELETE',
        data: {
          user: row[config.id]
        },
        error: function () {
          alertMessage('User deletion failed!', 'warning', 2000)
        },
        success: function () {
          $('.loader').addClass('d-none')
          alertMessage(row[config.id] + ' is deleted successfully!', 'info', 2000)
          $('.formhandler' + ' tr[data-row="' + rowNo + '"]').hide()
        }
      })
    },
    'reset_password': function (row) {
      $.ajax(config.login_url +'?'+ config.forgot_key, {
        method: 'POST',
        data: {
          user: row[config.id]
        },
        error: function () {
          alertMessage('Reset password email failed!', 'warning', 2000)
        },
        success: function() {
          alertMessage('Reset password email sent successfully!', 'info', 2000)
        }
      })
    }
  }

})

// This file is compiled into schedule.js via "yarn run build".
// Changing it has no impact.Compile before checking output.

import {
  base_template, name_template, actions_schedule_template, actions_alert_template,
  function_template, schedule_template, notification_template
} from './schedule.template.html'

var notification_msg = _.template(notification_template)

function notify(el, obj) {
  $(el)
    .prepend(notification_msg(obj))
    .get(0).scrollIntoView()
}

$.fn.schedule = function(options) {
  this.each(function () {
    var self = $(this)
    self.html(base_template)
    var logs = self.find('.schedule-logs')
    self.find('.schedule-formhandler').formhandler({
      src: options.url,
      columns: [
        { name: 'actions', template: options.alert ? actions_alert_template : actions_schedule_template },
        { name: 'name', template: name_template },
        { name: 'function', template: function_template },
        { name: 'next', title: 'schedule', type: 'date', template: schedule_template },
        { name: 'startup' },
        { name: 'thread' }
      ],
      page: false,
      pageSize: 1000,
      export: false
    })
    self.on('click', '.run', function () {
      var $this = $(this)
      var $icon = $('.fa', this).toggleClass('fa-play fa-spinner fa-spin')
      $icon.parent('.btn').prop('disabled', true)
      var name = $this.data('name')
      var shortname = _.last((name || '').split(/:/))
      $.ajax(options.url, {
        method: 'POST',
        data: { name: name, _xsrf: options.xsrf, mock: $this.data('mock') }
      }).done(function (results) {
        notify(logs, { name: shortname, results: results, mock: $this.data('mock') })
      }).fail(function (xhr, err, msg) {
        var error = $(xhr.responseText)
        notify(logs, {
          name: shortname,
          results: [],
          error: error.filter('section.content').find('pre').html() || msg || 'Error',
          traceback: error.filter('#traceback').html() || 'Unknown error'
        })
      }).always(function () {
        $icon.toggleClass('fa-play fa-spinner fa-spin')
        $icon.parent('.btn').prop('disabled', false)
      })
    })
  })
}

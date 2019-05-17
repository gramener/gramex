(function (factory) {
  typeof define === 'function' && define.amd ? define(factory) :
  factory();
}(function () { 'use strict';

  var base_template = "<div class=\"schedule-formhandler\"></div><div class=\"schedule-logs\"></div>";
  var name_template = "<td><%- _.last((obj.value || '').split(/:/)) %></td>";
  var actions_schedule_template = "<td><button class=\"run btn btn-primary btn-xs\" title=\"Run now\" data-name=\"<%- row.name %>\"><i class=\"fa fa-play\"></i></button></td>";
  var actions_alert_template = "<td><button class=\"run btn btn-primary btn-xs\" title=\"Send alert now\" data-name=\"<%- row.name %>\"><i class=\"fa fa-envelope\"></i></button><button class=\"run btn btn-success btn-xs ml-1\" title=\"Preview results\" data-name=\"<%- row.name %>\" data-mock=\"true\"><i class=\"fa fa-eye\"></i></button></td>";
  var notification_template = "<div class=\"alert alert-<%- obj.error ? 'danger' : 'success' %> alert-dismissible fade show\" role=\"alert\"><button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-label=\"Close\"><span aria-hidden=\"true\">×</span></button><div><strong><%- name %></strong> <% if (obj.error) { %> <%= obj.traceback || '' %> <% } else { %> <div><%- obj.mock ? 'Previewed successfully.' : 'Ran successfully.' %></div> <% } %> </div> <% _.each(obj.results, function (row) { %> <table class=\"table table-sm bg-white mt-3\"><tbody> <% _.each(['to', 'cc', 'bcc', 'from', 'reply_to', 'on_behalf_of', 'subject'], function (key) { %> <% if (key in row) { %> <tr><th><%- key %></th><td><%- row[key] %></td></tr> <% } %> <% }) %> <% if (row.body) { %><tr><th>body</th><td><%- row.body %></td></tr><% } %> <% if (row.html) { %><tr><th>html</th><td><%= row.html %></td></tr><% } %> <% if (row.attachments) { %> <tr><th>attachments</th><td><ul> <% _.each(row.attachments, function (path) { %> <li><%- path %></li> <% }) %> </ul></td></tr> <% } %> </tbody></table> <% }) %> </div>";
  var function_template = "<td><pre class=\"mb-0 pre-wrap\"><%- value %></pre> <% var args = JSON.parse(row.args), kwargs = JSON.parse(row.kwargs) %> <% if (_.size(args) + _.size(kwargs)) { %> <div><a data-toggle=\"collapse\" href=\"#kwargs<%- index %>\" class=\"sm1\">Expand arguments...</a></div><div class=\"collapse\" id=\"kwargs<%- index %>\"> <%= _.size(args) ? '<pre>' + JSON.stringify(args, null, 2) + '</pre>' : '' %> <%= _.size(kwargs) ? '<pre>' + JSON.stringify(kwargs, null, 2) + '</pre>' : '' %> </div> <% } %> </td>";
  var schedule_template = "<td><div><%- row.schedule %></div><div class=\"small\"><%- row.next ? moment.utc(row.next).fromNow() : '' %></div></td>";

  // This file is compiled into schedule.js via "yarn run build".

  var notification_msg = _.template(notification_template);

  function notify(el, obj) {
    $(el)
      .prepend(notification_msg(obj))
      .get(0).scrollIntoView();
  }

  $.fn.schedule = function(options) {
    this.each(function () {
      var self = $(this);
      self.html(base_template);
      var logs = self.find('.schedule-logs');
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
      });
      self.on('click', '.run', function () {
        var $this = $(this);
        var $icon = $('.fa', this).toggleClass('fa-play fa-spinner fa-spin');
        $icon.parent('.btn').prop('disabled', true);
        var name = $this.data('name');
        var shortname = _.last((name || '').split(/:/));
        $.ajax(options.url, {
          method: 'POST',
          data: { name: name, _xsrf: options.xsrf, mock: $this.data('mock') }
        }).done(function (results) {
          notify(logs, { name: shortname, results: results, mock: $this.data('mock') });
        }).fail(function (xhr, err, msg) {
          var error = $(xhr.responseText);
          notify(logs, {
            name: shortname,
            results: [],
            error: error.filter('section.content').find('pre').html() || msg || 'Error',
            traceback: error.filter('#traceback').html() || 'Unknown error'
          });
        }).always(function () {
          $icon.toggleClass('fa-play fa-spinner fa-spin');
          $icon.parent('.btn').prop('disabled', false);
        });
      });
    });
  };

}));

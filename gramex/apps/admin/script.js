/* global $, config_id, active_users */

// TODO: REVIEW: when users in auth.user.db are more than the number in lookup datasource, inform user
$('.formhandler').formhandler({
  columns: [
    {
      name: '*'
    },
    {
      name: config_id,
      format: function(user_id) {
        // TODO: after changing format option in g1 to use <%= instead of <%
        var isOnline = user_id in active_users ? '*' : ''
        return isOnline + user_id
      }
    }
  ],
  count: false,
  page: false,
  size: false,
  exportFormats: {
    xlsx: 'Excel'
  },
  filters: false
})

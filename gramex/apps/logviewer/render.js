/* globals d3 */
/* exported config */

var x_axis_format = "%d %b %Y";
var dt_axis_tickcount = { interval: "day", step: 1 };
var config = {
  filters: [
    {
      column: "status",
      type: "select",
      el: ".filter-status select",
      url: "query/aggD/filterstatus/",
    },
    {
      column: "user.id",
      type: "select",
      el: ".filter-users select",
      url: "query/aggD/filterusers/",
    },
    {
      column: "uri",
      type: "select",
      el: ".filter-uri select",
      url: "query/aggD/filteruri/",
    },
    {
      column: "ip",
      type: "select",
      el: ".filter-ip select",
      url: "query/aggD/filterip/",
    },
    { column: "time", type: "daterange", el: ".filter-time input", url: "" },
  ],
  viewsConfig: [
    {
      type: "kpi",
      url: "query/aggD/kpi-pageviews/",
      on: ".kpi-pageviews",
      formatter: d3.format(",.2d"),
    },
    {
      type: "kpi",
      url: "query/aggD/kpi-sessions/",
      on: ".kpi-sessions",
      keep: ["user.id", "time"],
      formatter: d3.format(",.2d"),
    },
    {
      type: "kpi",
      url: "query/aggD/kpi-users/",
      on: ".kpi-users",
      formatter: d3.format(",.2d"),
    },
    {
      type: "kpi",
      url: "query/aggD/kpi-avgtimespent/",
      on: ".kpi-avgtimespent",
      keep: ["user.id", "time"],
      formatter: function (v) {
        return d3.format(",.1f")(v / 60) + " min";
      },
    },
    {
      type: "kpi",
      url: "query/aggD/kpi-urls/",
      on: ".kpi-urls",
      formatter: d3.format(",.2d"),
    },
    {
      type: "kpi",
      url: "query/aggD/kpi-avgloadtime/",
      on: ".kpi-avgloadtime",
      formatter: function (v) {
        return d3.format(",.1f")(v) + " ms";
      },
    },
    {
      type: "viz",
      url: "query/aggD/pageviewstrend/",
      on: ".vegam-pageviewstrend",
      viz: [
        { data: null, options: { types: { time: "date" } } },
        {
          apply: "area",
          x: "time",
          y: "pageviews",
          props: { fill: "#c5e5f8" },
        },
        {
          apply: "line",
          x: "time",
          y: "pageviews",
          props: { stroke: "#186de5" },
        },
        {
          apply: "scatter",
          x: "time",
          y: "pageviews",
          mark: "circle",
          props: { fill: "#186de5", size: 50 },
        },
        {
          apply: "style",
          x_axis_format: x_axis_format,
          x_axis_tickCount: dt_axis_tickcount,
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/sessionstrend/",
      on: ".vegam-sessionstrend",
      keep: ["user.id", "time"],
      viz: [
        { data: null, options: { types: { time: "date" } } },
        { apply: "area", x: "time", y: "sessions", props: { fill: "#cc95ff" } },
        {
          apply: "line",
          x: "time",
          y: "sessions",
          props: { stroke: "#8f65b5" },
        },
        {
          apply: "scatter",
          x: "time",
          y: "sessions",
          mark: "circle",
          props: { fill: "#8f65b5", size: 50 },
        },
        {
          apply: "style",
          x_axis_format: x_axis_format,
          x_axis_tickCount: dt_axis_tickcount,
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/toptenuri/",
      on: ".vegam-toptenuri",
      viz: [
        { data: null },
        {
          apply: "bar",
          y: "uri",
          x: "views",
          order: "views",
          props: { fill: "#77b7f1" },
        },
        {
          apply: "style",
          y_sort_op: "sum",
          y_sort_field: "views",
          y_sort_order: "descending",
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/toptenusers/",
      on: ".vegam-toptenusers",
      viz: [
        { data: null },
        {
          apply: "bar",
          y: "[user.id]",
          x: "views",
          order: "views",
          props: { fill: "#8f65b5" },
        },
        {
          apply: "style",
          y_sort_op: "sum",
          y_sort_field: "views",
          y_sort_order: "descending",
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/toptenstatus/",
      on: ".vegam-toptenstatus",
      viz: [
        { data: null },
        {
          apply: "bar",
          y: "status",
          x: "requests",
          order: "requests",
          props: { fill: "#77b7f1" },
        },
        {
          apply: "style",
          y_sort_op: "sum",
          y_sort_field: "requests",
          y_sort_order: "descending",
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/toptenip/",
      on: ".vegam-toptenip",
      viz: [
        { data: null },
        {
          apply: "bar",
          y: "ip",
          x: "requests",
          order: "requests",
          props: { fill: "#8f65b5" },
        },
        {
          apply: "style",
          y_sort_op: "sum",
          y_sort_field: "requests",
          y_sort_order: "descending",
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/loadtimetrend/",
      on: ".vegam-loadtimetrend",
      viz: [
        { data: null, options: { types: { time: "date" } } },
        {
          apply: "line",
          x: "time",
          y: "loadtime",
          props: { stroke: "#ff8101" },
        },
        {
          apply: "scatter",
          x: "time",
          y: "loadtime",
          mark: "circle",
          props: { fill: "#ff8101", size: 50 },
        },
        {
          apply: "style",
          x_axis_format: x_axis_format,
          x_axis_tickCount: dt_axis_tickcount,
        },
      ],
    },
    {
      type: "viz",
      url: "query/aggD/loadtimerequeststrend/",
      on: ".vegam-loadtimerequeststrend",
      viz: [
        { data: null, options: { types: { time: "date" } } },
        { apply: "area", x: "time", y: "requests", props: { fill: "#cc95ff" } },
        { apply: "style", x_axis: null, y_axis_grid: false, n: -1 },
        {
          apply: "line",
          x: "time",
          y: "requests",
          props: { stroke: "#8f65b5" },
        },
        {
          apply: "scatter",
          x: "time",
          y: "requests",
          mark: "circle",
          props: { fill: "#8f65b5", size: 20 },
        },
        { apply: "style", x_axis: null, y_axis: null, n: -2 },
        {
          apply: "line",
          x: "time",
          y: "loadtime",
          props: { stroke: "#ff8101" },
        },
        {
          apply: "scatter",
          x: "time",
          y: "loadtime",
          mark: "circle",
          props: { fill: "#ff8101", size: 20 },
        },
        {
          apply: "style",
          x_axis_format: x_axis_format,
          x_axis_tickCount: dt_axis_tickcount,
          y_axis_grid: false,
          n: -2,
        },
        { apply: "resolve", scale_y: "independent" },
      ],
    },
  ],
};

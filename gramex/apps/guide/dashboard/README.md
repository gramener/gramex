---
title: Templatize visualization dashboard creation
prefix: DashboardHandler
...

[TOC]

Gramex can create dashboards using a simple `yaml` configuration.

    :::yaml
      polio:
        pattern: /$YAMLURL/polio
        handler: DashboardHandler
        kwargs:
          title: State-wise Polio cases from 1997 to 2017
          js: [jquery, bootstrap, d3, g, underscore]
          data:
            polio: {format: csv, file: $YAMLPATH/data/polio-cases-wildvirus.csv}
          navbar:
            logo: $YAMLPATH/logo.png
            filters: {data: polio, columns: ["State"]}
          "Heatmap of State vs Years":
            panel: vega-lite
            width: 12
            data: polio
            properties:
              mark: circle
              encoding:
                x: {field: State, type: ordinal}
                y: {field: 1997, type: number}
          "Andhra Pradesh":
            panel: vega-lite
            width: 6
            data: polio
            properties:
              mark: text
              encoding:
                row: {field: "State", type: ordinal}
                column: {field: 1997, type: ordinal}
                text: {aggregate: count, field: 1997, type: quantitative}
              config: {mark: {applyColorToBackground: true}}

Apart from the native charts, Gramex can use external libraries to create dashboards quickly. Here a Polio analysis dashboard with two charts, a navigation bar with `State` as a filter is created.

The dataset used for both the charts in the dashboard are `polio` defined in the parent `data` section. Multiple datasets can be used in a dashboard.

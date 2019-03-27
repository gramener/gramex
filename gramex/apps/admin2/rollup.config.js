import htmlparts from 'rollup-plugin-htmlparts'

export default [
  {
    input: 'schedule.src.js',
    output: { file: 'schedule.js', name: 'schedule', format: 'umd' },
    plugins: [
      htmlparts('schedule.template.html')
    ]
  }
]

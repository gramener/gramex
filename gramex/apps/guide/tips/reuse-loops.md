---
title: Iterate repeated code blocks with data
prefix: Tip
...

This is a fragment of code we deployed at a large bank to calculate year-on-year
growth of balance:

    :::python
    data['yoy_CDAB'] = map(
        calculate_calender_yoy,
        data['TOTAL_CDAB_x'],
        data['TOTAL_CDAB_y'])

On 29 Aug, the client added more metrics:

- CDAB: Cumulative Daily Average Balance (from start of year)
- MDAB: Monthly Daily Average Balance (from start of month)
- MEB: Month End Balance

This led to:

    :::python
    data['yoy_CDAB'] = map(
        calculate_calender_yoy,
        data['TOTAL_CDAB_x'],
        data['TOTAL_CDAB_y'])
    data['yoy_MDAB'] = map(
        calculate_calender_yoy,
        data['TOTAL_MDAB_x'],
        data['TOTAL_MDAB_y'])
    data['yoy_MEB'] = map(
        calculate_calender_yoy,
        data['TOTAL_MEB_x'],
        data['TOTAL_MEB_y'])

On 31 Aug, the client wanted to see this for different areas:

- NTB: New to Bank accounts (clients added in the last 2 years)
- ETB: Existing to Bank accounts (clients older than 2 years)
- Total: All Bank accounts

This led to:

    :::python
    data['yoy_CDAB'] = map(
        calculate_calender_yoy,
        data['TOTAL_CDAB_x'],
        data['TOTAL_CDAB_y'])
    data['yoy_MDAB'] = map(
        calculate_calender_yoy,
        data['TOTAL_MDAB_x'],
        data['TOTAL_MDAB_y'])
    data['yoy_MEB'] = map(
        calculate_calender_yoy,
        data['TOTAL_MEB_x'],
        data['TOTAL_MEB_y'])

    total_data['yoy_CDAB'] = map(
        calculate_calender_yoy,
        total_data['TOTAL_CDAB_x'],
        total_data['TOTAL_CDAB_y'])
    total_data['yoy_MDAB'] = map(
        calculate_calender_yoy,
        total_data['TOTAL_MDAB_x'],
        total_data['TOTAL_MDAB_y'])
    total_data['yoy_MEB'] = map(
        calculate_calender_yoy,
        total_data['TOTAL_MEB_x'],
        total_data['TOTAL_MEB_y'])

    etb_data['yoy_CDAB'] = map(
        calculate_calender_yoy,
        etb_data['TOTAL_CDAB_x'],
        etb_data['TOTAL_CDAB_y'])
    etb_data['yoy_MDAB'] = map(
        calculate_calender_yoy,
        etb_data['TOTAL_MDAB_x'],
        etb_data['TOTAL_MDAB_y'])
    etb_data['yoy_MEB'] = map(
        calculate_calender_yoy,
        etb_data['TOTAL_MEB_x'],
        etb_data['TOTAL_MEB_y'])

The above code that actually deployed in production.

[code]: https://code.gramener.com/axis/axis-coe/blob/master/balances/balance_distribution.py

**Loops avoid duplication**.

Whenever you see code copy-pasted with a few changes, use loops.

    :::python
    for area in [data, total_data, etb_data]:
        for val in ['CDAB', 'MDAB', 'MEB']:
            area['yoy_' + val] = map(
                calculate_calendar_yoy,
                area['TOTAL_' + val + '_x'],
                area['TOTAL_' + val + '_y'])

This reduces 39 lines to 7 - and makes it easier to add more areas and metrics.

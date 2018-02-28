---
title: Group common code into functions
prefix: Tip
...

When the same code is repeated *across different functions* like this:

    :::python
    def insert_l1_file(new_lst):
        data = pd.read_csv(filepath)
        data = data.fillna('')
        data = data.rename(columns=lambda x: str(x).replace('\r', ''))
        insertion_time = time.strftime("%d/%m/%Y %H:%M:%S")
        # ... more code

    def insert_l2_file(psu_name, value_lst, filepath, header_lst, new_package, id):
        data = pd.read_csv(filepath)
        data = data.fillna('')
        data = data.rename(columns=lambda x: str(x).replace('\r', ''))
        insertion_time = time.strftime("%d/%m/%Y %H:%M:%S")
        # ... more code

    def insert_key_details(psu_name, value_lst, filepath, header_lst):
        data = pd.read_csv(filepath)
        data = data.fillna('')
        data = data.rename(columns=lambda x: str(x).replace('\r', ''))
        insertion_time = time.strftime("%d/%m/%Y %H:%M:%S")
        # ... more code

... create a common function and call it.

    :::python
    def load_data(filepath):
        data = pd.read_csv(filepath)
        data = data.fillna('')
        data = data.rename(columns=lambda x: str(x).replace('\r', ''))
        insertion_time = time.strftime("%d/%m/%Y %H:%M:%S")
        return data, insertion_time

    def insert_l1_file(new_lst):
        data, insertion_time = load_data(filepath)
        # ... more code

    def insert_l2_file(psu_name, value_lst, filepath, header_lst, new_package, id):
        data, insertion_time = load_data(filepath)
        # ... more code

    def insert_key_details(psu_name, value_lst, filepath, header_lst):
        data, insertion_time = load_data(filepath)
        # ... more code

## But operations are still different

For `PSU_Personnel.csv`, we want to sort the records. Not for the others.

In that case, this is a **BAD** thing do do.

    :::python
    data = {key: pd.read_csv(info['file']) for key, info in lookup.items()}
    data['l3'].sort()

A better thing to do is:

    :::python
    lookup = {                             # Define a transformation for each file
        'l1': dict(file='PSU_l1.csv',        transform=lambda x: x),
        'l2': dict(file='PSU_l2.csv',        transform=lambda x: x),
        'l3': dict(file='PSU_Personnel.csv', transform=lambda x: x.sort()),
    }
    data = {
        key: info['transform'](pd.read_csv(info['file']))
        for key, info in lookup.items()
    }
    result = data[form_type][:lookup[form_type]['row']]

This lets you define arbitrary transformations for each dataset.

## But variable names are a given

If you cannot control the variable names (e.g. someone else has written that
code), and you *must* use the given variables `data_l1`, `data_l2`, etc., you
*could* use `locals()` like this:

    :::python
    result = locals().get('data_' + form_type)[:-1]

But re-structuring the code, if you can, is much better.
